import { getHotels, Hotel } from '@/lib/hotels'

export default async function HotelsPage() {
  const hotels = await getHotels()

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Hotels in Bora Bora</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {hotels.map((hotel: Hotel) => (
          <div key={hotel.slug} className="border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            <div className="p-4">
              <h2 className="text-xl font-semibold mb-2">
                <a href={`/hotels/${hotel.slug}`} className="hover:text-blue-600">
                  {hotel.title}
                </a>
              </h2>
              <div className="flex gap-2 text-sm text-gray-600 mb-2">
                <span className="bg-gray-100 px-2 py-1 rounded">{hotel.hotel_chain}</span>
                <span className="bg-gray-100 px-2 py-1 rounded">{hotel.hotel_brand}</span>
              </div>
              <div className="text-sm text-gray-600">
                <p>Destination: {hotel.destination}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
} 