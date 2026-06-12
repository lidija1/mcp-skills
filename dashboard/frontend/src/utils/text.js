export function cleanDisplayText(value) {
  if (value == null) return value
  return String(value)
    .replaceAll('Ã¢â‚¬â€', '-')
    .replaceAll('Ã¢â‚¬â€œ', '-')
    .replaceAll('Ã¢â‚¬Â¢', '*')
    .replaceAll('Ã¢â‚¬Â¦', '...')
    .replaceAll('â€”', '-')
    .replaceAll('â€“', '-')
    .replaceAll('â€¦', '...')
    .replaceAll('—', '-')
    .replaceAll('–', '-')
    .replaceAll('…', '...')
}

export function truncateDisplayText(value, maxLength = 80) {
  const text = cleanDisplayText(value ?? '').replace(/\s+/g, ' ').trim()
  if (text.length <= maxLength) return text

  const limit = Math.max(4, maxLength)
  let trimmed = text.slice(0, limit - 3)
  const lastSpace = trimmed.lastIndexOf(' ')
  if (lastSpace >= Math.floor(limit * 0.55)) {
    trimmed = trimmed.slice(0, lastSpace)
  }
  return `${trimmed.replace(/[,\s-]+$/g, '')}...`
}

export function summarizePersonaDescription(description = '', maxLength = 80) {
  const normalized = cleanDisplayText(description ?? '').replace(/\s+/g, ' ').trim()
  const parts = normalized.split(',').map(part => part.trim()).filter(Boolean)
  const lowerParts = parts.map(part => [part, part.toLowerCase()])
  const driver = (lowerParts.find(([, low]) => low.includes('driver'))?.[0] || '')
    .replace(/\b(adult\s+)?driver\b/gi, '')
    .trim()
  const genderPart = lowerParts.find(([, low]) => low.includes('female driver') || low.includes('male driver'))?.[1] || ''
  const gender = genderPart.includes('female driver') ? 'female' : genderPart.includes('male driver') ? 'male' : ''
  const driverBits = [driver, gender]
    .filter(bit => bit && !driver.toLowerCase().includes(bit))
    .join(' ')
  const coverage = (lowerParts.find(([, low]) => low.endsWith('coverage'))?.[0] || '')
    .replace(/\s+coverage$/i, '')
    .trim()
  const cleanRecord = lowerParts.find(([, low]) => low.includes('clean record'))?.[0] || ''
  const license = (lowerParts.find(([, low]) => low.endsWith('license status'))?.[0] || '')
    .replace(/\s+license status$/i, '')
    .trim()
  const vehicleUse = (lowerParts.find(([, low]) => low.endsWith('vehicle use') || low.endsWith(' use'))?.[0] || '')
    .replace(/\s+vehicle\s+use$/i, ' use')
    .trim()
  const sr22Part = lowerParts.find(([, low]) => low.includes('sr-22'))?.[1] || ''
  const sr22 = sr22Part.includes('without sr-22') ? 'no SR-22' : sr22Part ? 'SR-22' : ''
  const summary = [driverBits, coverage, cleanRecord, license, vehicleUse, sr22]
    .filter(Boolean)
    .join(', ')

  return truncateDisplayText(summary || normalized, maxLength)
}
