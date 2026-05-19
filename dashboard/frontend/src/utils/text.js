export function cleanDisplayText(value) {
  if (value == null) return value
  return String(value)
    .replaceAll('â€”', '-')
    .replaceAll('â€“', '-')
    .replaceAll('â€¢', '*')
    .replaceAll('â€¦', '...')
}
