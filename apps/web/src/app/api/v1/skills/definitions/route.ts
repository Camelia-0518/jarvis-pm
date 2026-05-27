import { NextResponse } from 'next/server'
import { skillRegistry } from '@/services/skills/registry'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)

  const category = searchParams.get('category')
  const agentRole = searchParams.get('agent_role')
  const searchQuery = searchParams.get('search')

  let skills = skillRegistry.getAllSkills()

  if (category) {
    skills = skills.filter((s) => s.category === category)
  }

  if (agentRole) {
    skills = skills.filter((s) => s.agentRole === agentRole)
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase()
    skills = skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags?.some((tag) => tag.toLowerCase().includes(q))
    )
  }

  return NextResponse.json({
    skills,
    total: skills.length,
  })
}
