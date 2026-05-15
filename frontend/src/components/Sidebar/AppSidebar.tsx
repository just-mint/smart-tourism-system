import {
  Landmark,
  LayoutDashboard,
  Map,
  Package,
  PackageOpen,
  Route,
  ScanFace,
  Settings,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const mainItems: Item[] = [
  { icon: LayoutDashboard, title: "Dashboard", path: "/" },
  { icon: Map, title: "Spatial Operations", path: "/spatial" },
  { icon: Route, title: "Smart Planner", path: "/itinerary" },
  { icon: Landmark, title: "Culture & Heritage", path: "/culture" },
  { icon: PackageOpen, title: "Inventory & O2O", path: "/inventory" },
  { icon: ScanFace, title: "Vision & Closet", path: "/vision" },
  { icon: Package, title: "Items", path: "/items" },
  { icon: Settings, title: "Settings", path: "/settings" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = currentUser?.is_superuser
    ? [...mainItems, { icon: Users, title: "Admin", path: "/admin" }]
    : mainItems

  return (
    <Sidebar
      collapsible="icon"
      className="border-r border-white/5 bg-black/40 backdrop-blur-xl"
    >
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
<<<<<<< HEAD
        <User user={currentUser} />
=======
        <User user={currentUser ?? null} />
>>>>>>> origin/main
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
