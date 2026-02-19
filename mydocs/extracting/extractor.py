"""Core extraction pipeline using LangGraph.

Graph structure:
  Subgraph: START → get_prompt_input → retriever_step → get_context → llm_step → enrich_step → END
  Main:     START --Send()--> [GROUP_SUBGRAPH...] → combine_results → END
"""

import json
from typing import Any

import litellm
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from tinystructlog import get_logger

from mydocs.extracting.context import (
    fields_to_query,
    format_fields_for_prompt,
    get_context,
    get_prompt_input,
)
from mydocs.extracting.enrichment import (
    _detect_composite_items,
    _extract_parent_name,
    enrich_composite_field_results,
    enrich_field_results,
)
from mydocs.extracting.models import (
    ContentMode,
    ExtractionMode,
    ExtractionRequest,
    ExtractionResponse,
    ExtractGroupState,
    ExtractorState,
    FieldDefinition,
    FieldResult,
    FieldResultRecord,
    LLMFieldsResult,
    ReferenceGranularity,
    RetrieverFilter,
    SubgraphOutput,
)
from mydocs.extracting.prompt_utils import (
    get_all_fields,
    get_field_groups,
    get_prompt,
    validate_field_consistency,
    validate_prompt_consistency,
)
from mydocs.extracting.registry import get_retriever, get_schema, get_target_object_class
from mydocs.extracting.target_objects import populate_target_object
from mydocs.models import Case, Document

log = get_logger(__name__)


class BaseExtractor:
    """LangGraph-based field extraction pipeline.

    Accepts an ExtractionRequest, resolves configuration, runs the
    extraction graph, and returns an ExtractionResponse.
    """

    def __init__(self, request: ExtractionRequest):
        self.request = request
        self.case_type = request.case_type
        self.document_type = request.document_type

    async def _resolve_case_type(self) -> str:
        """Resolve case_type from Case.type if case_id is provided."""
        if self.request.case_id:
            case = await Case.aget(self.request.case_id)
            if case:
                return case.type
            log.warning(f"Case {self.request.case_id} not found, using request case_type")
        return self.request.case_type

    def _build_initial_state(
        self,
        case_type: str,
        field_definitions: list[FieldDefinition],
        field_groups: dict[int, list[FieldDefinition]],
    ) -> ExtractorState:
        """Build the initial ExtractorState from the request."""
        return ExtractorState(
            case_id=self.request.case_id,
            case_type=case_type,
            document_type=self.document_type,
            document_ids=self.request.document_ids or [],
            page_ids=self.request.page_ids,
            subdocument_id=self.request.subdocument_id or "",
            extraction_mode=self.request.extraction_mode,
            output_schema_name=self.request.output_schema or "default",
            infer_references=self.request.infer_references,
            reference_granularity=self.request.reference_granularity,
            content_mode=self.request.content_mode,
            field_definitions=field_definitions,
            field_groups=field_groups,
            retriever_filter=RetrieverFilter(
                document_ids=self.request.document_ids,
                page_ids=self.request.page_ids,
            ),
        )

    async def _resolve_subdocument(self) -> None:
        """If subdocument_id is provided, scope extraction to the subdocument."""
        if not self.request.subdocument_id or not self.request.document_ids:
            return

        doc = await Document.aget(self.request.document_ids[0])
        if not doc or not doc.subdocuments:
            log.warning(f"No subdocuments on document {self.request.document_ids[0]}")
            return

        subdoc = next(
            (s for s in doc.subdocuments if s.id == self.request.subdocument_id),
            None,
        )
        if not subdoc:
            log.warning(f"SubDocument {self.request.subdocument_id} not found")
            return

        # Override document_type from subdocument
        self.document_type = subdoc.document_type
        self.case_type = subdoc.case_type

        # Scope page_ids to subdocument's pages
        self.request.page_ids = [pr.page_id for pr in subdoc.page_refs]

        log.info(
            f"Scoped to subdocument {subdoc.id}: "
            f"type={subdoc.document_type}, pages={len(subdoc.page_refs)}"
        )

    async def run(self) -> ExtractionResponse:
        """Execute the full extraction pipeline."""
        # Step 1: Initialize
        case_type = await self._resolve_case_type()
        self.case_type = case_type

        # Subdocument scoping
        await self._resolve_subdocument()
        case_type = self.case_type  # May have been overridden by subdocument

        # Load field definitions
        field_definitions = get_all_fields(case_type, self.document_type)

        # Apply field_overrides
        if self.request.field_overrides:
            override_names = {f.name for f in self.request.field_overrides}
            field_definitions = [
                f for f in field_definitions if f.name not in override_names
            ]
            field_definitions.extend(self.request.field_overrides)

        # Filter to requested fields
        if self.request.fields:
            requested = set(self.request.fields)
            field_definitions = [f for f in field_definitions if f.name in requested]

        # Group fields
        field_groups = {}
        for field in field_definitions:
            field_groups.setdefault(field.group, []).append(field)

        # Load prompt configs for each group
        prompt_configs = {}
        for group_id in field_groups:
            prompt_config = get_prompt(case_type, self.document_type, group_id)
            validate_prompt_consistency(prompt_config)
            validate_field_consistency(field_definitions, prompt_config)
            prompt_configs[group_id] = prompt_config

        # Build initial state
        state = self._build_initial_state(case_type, field_definitions, field_groups)
        state.prompt_configs = prompt_configs

        # Step 2: Execute groups in parallel via LangGraph
        all_field_results: dict[str, FieldResult] = {}
        all_composite_results: dict[str, list[dict[str, FieldResult]]] = {}
        model_used = "unknown"

        for group_id, fields in field_groups.items():
            prompt_config = prompt_configs[group_id]
            model_used = prompt_config.model

            group_state = ExtractGroupState(
                group_id=group_id,
                fields=fields,
                prompt_config=prompt_config,
                retriever_filter=state.retriever_filter,
                extraction_mode=self.request.extraction_mode,
                content_mode=self.request.content_mode,
                reference_granularity=self.request.reference_granularity,
                output_schema_name=self.request.output_schema or "default",
            )

            group_result = await self._run_group(group_state)
            all_field_results.update(group_result.field_results)
            for k, v in group_result.composite_results.items():
                all_composite_results.setdefault(k, []).extend(v)

        # Step 3: Combine results
        results_dict = {
            name: result.model_dump() for name, result in all_field_results.items()
        }
        # Serialize composite results into results_dict
        for parent_name, items in all_composite_results.items():
            results_dict[parent_name] = [
                {k: v.model_dump() for k, v in item.items()}
                for item in items
            ]

        # Step 5: Save results and target object
        target_object_id = None
        if self.request.document_ids:
            for doc_id in self.request.document_ids:
                await self._save_results(doc_id, all_field_results)
                tid = await self._save_target_object(
                    doc_id, all_field_results, all_composite_results
                )
                if tid:
                    target_object_id = tid

        # Return response
        return ExtractionResponse(
            document_id=self.request.document_ids[0] if self.request.document_ids else "",
            document_type=self.document_type,
            case_type=case_type,
            extraction_mode=self.request.extraction_mode,
            results=results_dict,
            subdocument_id=self.request.subdocument_id,
            target_object_id=target_object_id,
            model_used=model_used,
            reference_granularity=self.request.reference_granularity,
        )

    async def _run_group(self, group_state: ExtractGroupState) -> SubgraphOutput:
        """Execute a single extraction group: prompt → retrieve → context → llm → enrich."""
        prompt_config = group_state.prompt_config
        if not prompt_config:
            log.error(f"No prompt config for group {group_state.group_id}")
            return SubgraphOutput()

        # 2a. Build prompt input
        document_id = ""
        if group_state.retriever_filter and group_state.retriever_filter.document_ids:
            document_id = group_state.retriever_filter.document_ids[0]

        prompt_input = await get_prompt_input(
            group_state.fields,
            document_id,
            self.document_type,
            subdocument_id=self.request.subdocument_id or "",
        )
        group_state.prompt_input = prompt_input

        # 2b. Retrieve context
        retriever_config = prompt_config.retriever_config
        if retriever_config:
            retriever_fn = get_retriever(retriever_config.name)
            query = fields_to_query(group_state.fields)
            pages = await retriever_fn(
                query, retriever_config, group_state.retriever_filter
            )
            group_state.retrieved_pages = pages
        else:
            group_state.retrieved_pages = []

        # 2c. Build context string
        context, doc_short_to_long = get_context(
            group_state.retrieved_pages,
            group_state.content_mode,
        )
        group_state.context = context
        group_state.doc_short_to_long = doc_short_to_long

        # 2d. LLM call
        fields_str = format_fields_for_prompt(prompt_input.field_prompts)

        # Add field inputs if available
        if prompt_input.field_inputs:
            inputs_str = "\n".join(
                f"- {fi.field_name}: {fi.content or 'N/A'}"
                for fi in prompt_input.field_inputs
            )
            fields_str += f"\n\nPreviously extracted values:\n{inputs_str}"

        # Get output schema
        output_schema = get_schema(group_state.output_schema_name)

        # Fill templates
        sys_prompt = prompt_config.sys_prompt_template
        if "{FIELD_SCHEMA}" in sys_prompt:
            schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
            sys_prompt = sys_prompt.replace("{FIELD_SCHEMA}", schema_json)

        user_prompt = prompt_config.user_prompt_template.format(
            fields=fields_str,
            context=context,
        )

        # Call LLM with structured output
        llm_result = await self._call_llm(
            sys_prompt, user_prompt, prompt_config, output_schema
        )
        group_state.llm_result = llm_result

        # 2e. Enrich results
        if isinstance(llm_result, LLMFieldsResult):
            field_results = await enrich_field_results(
                llm_result.result,
                doc_short_to_long,
                group_state.reference_granularity,
                prompt_config.model,
            )
            group_state.field_results = field_results
            return SubgraphOutput(field_results=field_results)
        elif _detect_composite_items(llm_result):
            parent_name = _extract_parent_name(group_state.fields)
            composite_results = await enrich_composite_field_results(
                llm_result.result,
                doc_short_to_long,
                group_state.reference_granularity,
                prompt_config.model,
                parent_name,
            )
            return SubgraphOutput(composite_results=composite_results)
        else:
            # Direct mode or custom schema — store raw result
            field_results = {}
            if hasattr(llm_result, "result") and isinstance(llm_result.result, list):
                for i, item in enumerate(llm_result.result):
                    field_results[f"item_{i}"] = FieldResult(
                        content=json.dumps(item.model_dump() if hasattr(item, "model_dump") else item),
                        created_by=prompt_config.model,
                    )
            group_state.field_results = field_results
            return SubgraphOutput(field_results=field_results)

    async def _call_llm(
        self,
        sys_prompt: str,
        user_prompt: str,
        prompt_config: Any,
        output_schema: type,
    ) -> Any:
        """Call the LLM with structured output via litellm.

        Uses a two-level retry strategy:
        - Transport retries (transport_retries): Handled by litellm internally
          for HTTP 429, 500, 503, connection errors, and timeouts.
        - Validation retries (validation_retries): Outer loop retries when the
          LLM returns valid JSON that fails Pydantic model_validate_json().
        """
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error = None
        for attempt in range(prompt_config.validation_retries):
            try:
                response = await litellm.acompletion(
                    model=prompt_config.model,
                    messages=messages,
                    response_format=output_schema,
                    num_retries=prompt_config.transport_retries,
                    **prompt_config.llm_kwargs,
                )

                content = response.choices[0].message.content
                return output_schema.model_validate_json(content)

            except litellm.exceptions.APIError:
                raise  # Transport errors already retried by litellm; don't retry again

            except Exception as e:
                last_error = e
                log.warning(
                    f"Validation attempt {attempt + 1}/{prompt_config.validation_retries} "
                    f"failed: {e}"
                )

        raise last_error

    async def _save_results(
        self,
        document_id: str,
        field_results: dict[str, FieldResult],
    ) -> None:
        """Save extraction results to the field_results collection."""
        subdocument_id = self.request.subdocument_id or ""
        for field_name, result in field_results.items():
            record = FieldResultRecord(
                document_id=document_id,
                document_type=self.document_type,
                subdocument_id=subdocument_id,
                case_type=self.case_type,
                field_name=field_name,
                result=result,
            )
            await record.asave()
            log.debug(f"Saved field result: {document_id}/{field_name}")

    async def _save_target_object(
        self,
        document_id: str,
        field_results: dict[str, FieldResult],
        composite_results: dict[str, list[dict[str, FieldResult]]] | None = None,
    ) -> str | None:
        """Save a target object if one is registered for this (case_type, document_type)."""
        target_cls = get_target_object_class(self.case_type, self.document_type)
        if not target_cls:
            return None

        subdocument_id = self.request.subdocument_id or ""

        target_obj = target_cls(
            document_id=document_id,
            subdocument_id=subdocument_id,
            case_id=self.request.case_id or "",
        )
        populate_target_object(target_obj, field_results, composite_results)
        await target_obj.asave()

        target_id = str(target_obj.id)
        log.info(
            f"Saved target object {target_cls.__name__} "
            f"(id={target_id}) for {self.case_type}/{self.document_type}"
        )
        return target_id
