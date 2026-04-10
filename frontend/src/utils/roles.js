export function formatRoleName(role) {
  return (role || 'intern')
    .split(' ')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function isAdminRole(role) {
  return (role || '').toLowerCase() === 'admin'
}

export function getRoleTheme(role) {
  const normalized = (role || '').toLowerCase()
  if (normalized === 'admin') {
    return {
      color: 'text-purple-400',
      badgeColor: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
      label: 'ADMIN',
      desc: 'Full access granted',
      badge: '⬡ ADMIN',
    }
  }
  if (normalized === 'hr') {
    return {
      color: 'text-warn',
      badgeColor: 'text-warn bg-warn/10 border-warn/20',
      label: 'HR',
      desc: 'PII-aware access',
      badge: '◈ HR',
    }
  }
  return {
    color: 'text-accent',
    badgeColor: 'text-accent bg-accent/10 border-accent/20',
    label: formatRoleName(normalized).toUpperCase(),
    desc: 'Governed enterprise access',
    badge: `◎ ${formatRoleName(normalized).toUpperCase()}`,
  }
}
