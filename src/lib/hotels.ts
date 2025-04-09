import { promises as fs } from 'fs'
import path from 'path'
import matter from 'gray-matter'

export interface Hotel {
  slug: string
  title: string
  destination: string
  hotel_chain: string
  hotel_brand: string
  content: string
}

export async function getHotels(): Promise<Hotel[]> {
  const hotelsDir = path.join(process.cwd(), 'src', 'contents', 'hotels')
  const files = await fs.readdir(hotelsDir)
  
  const hotels = await Promise.all(
    files.map(async (file) => {
      const originalFileName = file.replace('.md', '')
      const slug = originalFileName.toLowerCase().replace(/ /g, '-')
      const filePath = path.join(hotelsDir, file)
      const fileContent = await fs.readFile(filePath, 'utf-8')
      const { data, content } = matter(fileContent)
      
      return {
        slug,
        title: data.title || originalFileName,
        destination: data.destination || '',
        hotel_chain: data.hotel_chain || '',
        hotel_brand: data.hotel_brand || '',
        content
      }
    })
  )
  
  return hotels
}

export async function getHotel(slug: string): Promise<Hotel | null> {
  const hotels = await getHotels()
  return hotels.find(hotel => hotel.slug === slug) || null
} 