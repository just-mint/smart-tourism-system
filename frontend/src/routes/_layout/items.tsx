import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"

import { ItemsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddItem from "@/components/Items/AddItem"
import { columns } from "@/components/Items/columns"
import PendingItems from "@/components/Pending/PendingItems"

function getItemsQueryOptions() {
  return {
    queryFn: () => ItemsService.readItems({ skip: 0, limit: 100 }),
    queryKey: ["items"],
  }
}

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  head: () => ({
    meta: [
      {
        title: "Items - AEGIS O2O",
      },
    ],
  }),
})

function ItemsTableContent() {
  const { data: items } = useSuspenseQuery(getItemsQueryOptions())

  if (items.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center animate-in zoom-in duration-700">
        <div className="relative w-72 h-48 mb-8 flex items-center justify-center group">
          <img 
            src="https://images.unsplash.com/photo-1554350331-561ce1982b52?q=80&w=800" 
            alt="Vintage Trunk" 
            className="w-full h-full object-contain drop-shadow-2xl group-hover:scale-105 transition-transform duration-700"
          />
        </div>
        <h3 className="text-2xl font-bold text-zinc-900 mb-2 font-serif">Chưa có sản phẩm nào.</h3>
        <p className="text-zinc-600 text-sm max-w-xs leading-relaxed">
          Hãy bắt đầu hành trình của bạn bằng cách thêm sản phẩm mới.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden">
      <DataTable columns={columns} data={items.data} />
    </div>
  )
}

function ItemsTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <ItemsTableContent />
    </Suspense>
  )
}

function Items() {
  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-[#FDFBF7] via-[#FFF8F0] to-[#FFF3E0] font-sans text-zinc-900 selection:bg-amber-500/30 overflow-hidden relative">
      {/* Background Texture/Curves Simulation */}
      <div className="absolute top-0 left-0 w-full h-96 overflow-hidden pointer-events-none opacity-[0.35] mix-blend-multiply">
        <svg viewBox="0 0 1440 320" className="absolute top-0 left-0 w-full h-full preserve-3d">
          <path fill="#F4E3C5" fillOpacity="1" d="M0,160L48,144C96,128,192,96,288,106.7C384,117,480,171,576,192C672,213,768,203,864,170.7C960,139,1056,85,1152,74.7C1248,64,1344,96,1392,112L1440,128L1440,0L1392,0C1344,0,1248,0,1152,0C1056,0,960,0,864,0C768,0,672,0,576,0C480,0,384,0,288,0C192,0,96,0,48,0L0,0Z"></path>
          <path fill="#D4AF37" fillOpacity="0.1" d="M0,32L80,37.3C160,43,320,53,480,85.3C640,117,800,171,960,192C1120,213,1280,203,1360,197.3L1440,192L1440,0L1360,0C1280,0,1120,0,960,0C800,0,640,0,480,0C320,0,160,0,80,0L0,0Z"></path>
        </svg>
      </div>

      <div className="max-w-[1600px] mx-auto flex flex-col animate-in fade-in duration-700 relative z-10 pt-12 px-6 md:px-10 gap-10">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 w-full mt-4">
          <div>
            <h1 className="text-4xl md:text-[2.75rem] font-bold text-zinc-900 font-serif mb-3 tracking-tight" style={{ color: '#2d2a26' }}>
              Quản lý Tài nguyên & Sản phẩm
            </h1>
            <p className="text-[15px] text-zinc-700 font-medium tracking-wide">
              Tạo & Quản lý tài nguyên cao cấp
            </p>
          </div>
          
          <div className="mt-2 md:mt-0 relative z-20">
             <div className="flex items-center gap-3">
               <AddItem />
             </div>
          </div>
        </div>
        
        {/* Table Container */}
        <div className="bg-white/95 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-6 md:p-10 min-h-[600px] flex flex-col justify-center">
           <ItemsTable />
        </div>
      </div>
    </div>
  )
}
