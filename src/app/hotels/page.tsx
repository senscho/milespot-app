import { promises as fs } from 'fs'
import path from 'path'
import Link from 'next/link'
import matter from 'gray-matter'

interface Hotel {
  slug: string
  title: string
  tags: string[]
}

async function getHotels(): Promise<Hotel[]> {
  const hotelsDir = path.join(process.cwd(), 'src', 'contents', 'hotels')
  const files = await fs.readdir(hotelsDir)
  
  const hotels = await Promise.all(
    files.map(async (file) => {
      const originalFileName = file.replace('.md', '')
      const slug = originalFileName.replace(/ /g, '-')
      const filePath = path.join(hotelsDir, file)
      const fileContent = await fs.readFile(filePath, 'utf-8')
      const { data } = matter(fileContent)
      
      return {
        slug,
        title: data.title || originalFileName,
        tags: data.tags || []
      }
    })
  )
  
  return hotels
}

export default async function HotelsPage() {
  const hotels = await getHotels()
  
  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-4xl font-bold mb-8">호텔 목록</h1>
      
      <div className="grid gap-6">
        {hotels.map((hotel) => (
          <Link 
            key={hotel.slug}
            href={`/hotels/${hotel.slug}`}
            className="block p-6 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h2 className="text-2xl font-semibold mb-2">{hotel.title}</h2>
            
            <div className="flex gap-2">
              {hotel.tags.map((tag) => (
                <span key={tag} className="bg-gray-100 px-3 py-1 rounded-full text-sm">
                  {tag}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
} 