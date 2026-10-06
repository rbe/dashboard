export type Link = {
  label: string
  href: string
  role: string
}

export type System = {
  id: string
  name: string
  subject: string
  summary: string
  note: string
  task: string
  tags: string[]
  pinned: boolean
  fields: Record<string, string>
  links: Link[]
}

export type View = 'cards' | 'list' | 'collapse'

export type Lang = 'en' | 'de'
