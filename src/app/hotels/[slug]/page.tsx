import { notFound } from 'next/navigation'
import { getHotel } from '@/lib/hotels'
import ReactMarkdown from 'react-markdown'

export default async function HotelPage({ params }: { params: { slug: string } }) {
  const hotel = await getHotel(params.slug)

  if (!hotel) {
    notFound()
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">{hotel.title}</h1>
      <div className="flex gap-2 text-sm text-gray-600 mb-4">
        <span className="bg-gray-100 px-2 py-1 rounded">{hotel.hotel_chain}</span>
        <span className="bg-gray-100 px-2 py-1 rounded">{hotel.hotel_brand}</span>
        <span className="bg-gray-100 px-2 py-1 rounded">{hotel.destination}</span>
      </div>
      <div className="prose max-w-none">
        <ReactMarkdown>{hotel.content}</ReactMarkdown>
      </div>
    </div>
  )
} 