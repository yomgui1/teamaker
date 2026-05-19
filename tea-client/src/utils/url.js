export function imageUrl(filename) {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  return `${base}/image/${filename}`
}
