import { promises as fs } from 'fs'
import path from 'path'
import { notFound } from 'next/navigation'
import matter from 'gray-matter'

interface Hotel {
  title: string
  content: string
  tags: string[]
}

async function getHotel(slug: string): Promise<Hotel | null> {
  try {
    // URL 슬러그를 원래 파일명으로 변환
    const originalFileName = slug.replace(/-/g, ' ')
    const filePath = path.join(process.cwd(), 'src', 'contents', 'hotels', `${originalFileName}.md`)
    const fileContent = await fs.readFile(filePath, 'utf-8')
    const { data, content } = matter(fileContent)
    
    return {
      title: data.title || originalFileName,
      content,
      tags: data.tags || []
    }
  } catch (error) {
    return null
  }
}

export default async function HotelPage({ params }: { params: { slug: string } }) {
  const hotel = await getHotel(params.slug)
  
  if (!hotel) {
    notFound()
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-4xl font-bold mb-6">{hotel.title}</h1>
      
      <div className="flex gap-2 mb-6">
        {hotel.tags.map((tag) => (
          <span key={tag} className="bg-gray-100 px-3 py-1 rounded-full text-sm">
            {tag}
          </span>
        ))}
      </div>

      <div className="prose prose-lg max-w-none">
        {hotel.content.split('\n').map((line, i) => {
          if (line.startsWith('- **')) {
            const [key, value] = line.replace('- **', '').split('**: ')
            return (
              <div key={i} className="mb-4">
                <strong className="text-lg">{key}:</strong> {value}
              </div>
            )
          }
          return <p key={i}>{line}</p>
        })}
      </div>
    </div>
  )
} 