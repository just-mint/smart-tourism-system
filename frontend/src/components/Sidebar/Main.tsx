import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import type { LucideIcon } from "lucide-react"
import { useEffect, useState } from "react"

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

export type Item = {
  icon: LucideIcon
  title: string
  path: string
}

interface MainProps {
  items: Item[]
}

export function Main({ items }: MainProps) {
  const { isMobile, setOpenMobile } = useSidebar()
  const router = useRouterState()
  const currentPath = router.location.pathname
  const [visibleItems, setVisibleItems] = useState<boolean[]>([])

  useEffect(() => {
    // Animation tuần tự xuất hiện
    const timeouts: NodeJS.Timeout[] = []
    items.forEach((_, idx) => {
      const timeout = setTimeout(() => {
        setVisibleItems((prev) => {
          const newArr = [...prev]
          newArr[idx] = true
          return newArr
        })
      }, idx * 50)
      timeouts.push(timeout)
    })
    return () => timeouts.forEach(clearTimeout)
  }, [items])

  const handleMenuClick = () => {
    if (isMobile) {
      setOpenMobile(false)
    }
  }

  return (
    <SidebarGroup className="px-2">
      <SidebarGroupContent>
        <SidebarMenu className="space-y-1">
          {items.map((item, index) => {
            const isActive = currentPath === item.path
            const isVisible = visibleItems[index]

            return (
              <SidebarMenuItem key={item.title}>
                <div
                  className={`
                    transition-all duration-300 ease-out
                    ${isVisible ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-2"}
                  `}
                  style={{ transitionDelay: `${index * 30}ms` }}
                >
                  <RouterLink
                    to={item.path}
                    onClick={handleMenuClick}
                    className={`
                      group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium
                      transition-all duration-300 ease-out
                      ${
                        isActive
                          ? "bg-gradient-to-r from-cyan-500/20 to-purple-500/20 text-white shadow-[0_0_12px_rgba(6,182,212,0.3)]"
                          : "text-zinc-400 hover:text-white hover:bg-white/5"
                      }
                    `}
                  >
                    {/* Active indicator bar */}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-cyan-400 to-purple-500" />
                    )}

                    {/* Icon */}
                    <div
                      className={`
                      relative flex h-5 w-5 items-center justify-center transition-all duration-300
                      ${
                        isActive
                          ? "text-cyan-400 drop-shadow-[0_0_5px_rgba(6,182,212,0.8)]"
                          : "text-zinc-500 group-hover:text-cyan-300"
                      }
                    `}
                    >
                      <item.icon className="h-5 w-5 transition-transform duration-200 group-hover:scale-110" />
                    </div>

                    {/* Title */}
                    <span
                      className={`
                      tracking-wide transition-all duration-200
                      ${isActive ? "font-semibold tracking-wider" : "group-hover:tracking-wider"}
                    `}
                    >
                      {item.title}
                    </span>
                  </RouterLink>
                </div>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
