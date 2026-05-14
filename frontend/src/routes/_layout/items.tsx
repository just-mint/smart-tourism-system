import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Package, Search } from "lucide-react"
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
      <div className="glass-card p-12 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
          <Search className="h-8 w-8 text-zinc-600" />
        </div>
        <h3 className="text-lg font-semibold text-zinc-300">No items yet</h3>
        <p className="text-zinc-500 text-sm mt-1">
          Add a new item to get started
        </p>
      </div>
    )
  }

  return (
    <div className="glass-card overflow-hidden">
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
    <div className="p-6 md:p-8 w-full max-w-[1800px] mx-auto flex flex-col gap-6 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 glow-cyan">
            <Package className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Items
            </h1>
            <p className="text-sm text-cyan-400/70 font-mono mt-0.5 tracking-widest uppercase">
              Create & Manage Resources
            </p>
          </div>
        </div>
        <AddItem />
      </div>
      <ItemsTable />
    </div>
  )
}
