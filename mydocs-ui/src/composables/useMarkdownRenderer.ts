import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: false,
})

export function useMarkdownRenderer() {
  function render(markdown: string): string {
    return md.render(markdown)
  }

  return { render }
}
