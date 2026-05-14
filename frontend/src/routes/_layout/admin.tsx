import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Check, Loader2, Shield, Star, X } from "lucide-react"
import { Suspense, useEffect, useState } from "react"
import { toast } from "sonner"

import { type UserPublic, UsersService } from "@/client"
import { CultureAPI, type ReviewResponse } from "@/client/aegis-api"
import AddUser from "@/components/Admin/AddUser"
import { columns, type UserTableData } from "@/components/Admin/columns"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import useAuth from "@/hooks/useAuth"

function getUsersQueryOptions() {
  return {
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
    queryKey: ["users"],
  }
}

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Admin - AEGIS O2O",
      },
    ],
  }),
})

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  return (
    <div className="glass-card overflow-hidden">
      <DataTable columns={columns} data={tableData} />
    </div>
  )
}

function UsersTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent />
    </Suspense>
  )
}

function ReviewModerationPanel() {
  const [reviews, setReviews] = useState<ReviewResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeId, setActiveId] = useState<number | null>(null)

  const loadReviews = async () => {
    setIsLoading(true)
    try {
      const res = await CultureAPI.getModerationReviews("pending")
      setReviews(res.data)
    } catch {
      toast.error("Không thể tải review chờ duyệt.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadReviews()
  }, [])

  const moderate = async (reviewId: number, status: "approved" | "rejected") => {
    setActiveId(reviewId)
    try {
      await CultureAPI.moderateReview(
        reviewId,
        status,
        status === "approved" ? "Approved by admin" : "Rejected by admin",
      )
      setReviews((prev) => prev.filter((review) => review.id !== reviewId))
      toast.success(status === "approved" ? "Đã duyệt review." : "Đã từ chối review.")
    } catch {
      toast.error("Không thể cập nhật trạng thái review.")
    } finally {
      setActiveId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Review Moderation</h2>
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">
            Pending culture reviews · approve before public display
          </p>
        </div>
        <button
          type="button"
          onClick={loadReviews}
          className="rounded-md border border-white/10 px-3 py-2 text-xs font-mono uppercase tracking-wider text-zinc-300 hover:border-cyan-400/40 hover:text-cyan-200"
        >
          Refresh
        </button>
      </div>

      <div className="glass-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center gap-2 p-6 text-sm text-zinc-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading reviews...
          </div>
        ) : reviews.length === 0 ? (
          <div className="p-6 text-sm text-zinc-500">
            Không có review nào đang chờ duyệt.
          </div>
        ) : (
          <div className="divide-y divide-white/10">
            {reviews.map((review) => (
              <div key={review.id} className="grid gap-4 p-5 md:grid-cols-[1fr_auto]">
                <div className="min-w-0">
                  <div className="mb-2 flex flex-wrap items-center gap-3">
                    <span className="font-semibold text-white">{review.author_name}</span>
                    <span className="rounded-full border border-amber-400/30 px-2 py-0.5 text-[10px] font-mono uppercase text-amber-200">
                      {review.status}
                    </span>
                    <span className="flex items-center gap-1">
                      {Array(5)
                        .fill(0)
                        .map((_, idx) => (
                          <Star
                            key={idx}
                            className={`h-3 w-3 ${idx < review.rating ? "fill-amber-300 text-amber-300" : "text-zinc-700"}`}
                          />
                        ))}
                    </span>
                  </div>
                  <p className="line-clamp-3 text-sm leading-6 text-zinc-300">
                    {review.text}
                  </p>
                  <p className="mt-2 text-xs font-mono text-zinc-600">
                    {review.time_posted} · reports: {review.report_count}
                  </p>
                </div>
                <div className="flex items-center gap-2 md:justify-end">
                  <button
                    type="button"
                    disabled={activeId === review.id}
                    onClick={() => moderate(review.id, "approved")}
                    className="inline-flex items-center gap-2 rounded-md bg-emerald-500/15 px-3 py-2 text-sm font-semibold text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" />
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={activeId === review.id}
                    onClick={() => moderate(review.id, "rejected")}
                    className="inline-flex items-center gap-2 rounded-md bg-red-500/15 px-3 py-2 text-sm font-semibold text-red-200 hover:bg-red-500/25 disabled:opacity-50"
                  >
                    <X className="h-4 w-4" />
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function Admin() {
  return (
    <div className="p-6 md:p-8 w-full max-w-[1800px] mx-auto flex flex-col gap-6 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20">
            <Shield className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Admin Panel
            </h1>
            <p className="text-sm text-red-400/70 font-mono mt-0.5 tracking-widest uppercase">
              User Management · Superuser Only
            </p>
          </div>
        </div>
        <AddUser />
      </div>
      <ReviewModerationPanel />
      <UsersTable />
    </div>
  )
}
