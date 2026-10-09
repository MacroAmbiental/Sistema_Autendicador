const TI_EMAILS = String(import.meta.env.VITE_TI_EMAILS || '')
  .split(',')
  .map((item) => item.trim().toLowerCase())
  .filter(Boolean)

function listFromClaim(value) {
  if (Array.isArray(value)) return value.map((item) => String(item).toLowerCase())
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  }
  return []
}

export async function hasTiPermission(user) {
  if (!user) return false

  const email = String(user.email || '').trim().toLowerCase()
  if (email && TI_EMAILS.includes(email)) return true

  const tokenResult = await user.getIdTokenResult()
  const role = String(tokenResult.claims?.role || '').toLowerCase()
  const roles = listFromClaim(tokenResult.claims?.roles)
  const perfil = String(tokenResult.claims?.perfil || '').toLowerCase()
  const perfis = listFromClaim(tokenResult.claims?.perfis)

  const granted = new Set([role, perfil, ...roles, ...perfis])
  return granted.has('ti') || granted.has('admin_ti') || granted.has('admin-ti') || granted.has('admin')
}
