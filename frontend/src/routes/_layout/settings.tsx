import { createFileRoute } from "@tanstack/react-router"
import { Settings as SettingsIcon } from "lucide-react"

import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"

const tabsConfig = [
  { value: "my-profile", title: "Hồ sơ", component: UserInformation },
  { value: "password", title: "Mật khẩu", component: ChangePassword },
  { value: "danger-zone", title: "Khu vực nguy hiểm", component: DeleteAccount },
]

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: "Cài đặt - AEGIS O2O",
      },
    ],
  }),
})

function UserSettings() {
  const { user: currentUser } = useAuth()
  const finalTabs = currentUser?.is_superuser
    ? tabsConfig.slice(0, 3)
    : tabsConfig

  if (!currentUser) {
    return null
  }

  return (
    <div className="p-6 md:p-8 w-full max-w-[1200px] mx-auto flex flex-col gap-6 animate-in fade-in duration-700">
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-xl bg-zinc-500/10 border border-zinc-500/20">
          <SettingsIcon className="w-6 h-6 text-zinc-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Cài đặt
          </h1>
          <p className="text-sm text-zinc-400/70 font-mono mt-0.5 tracking-widest uppercase">
            Tài khoản & tùy chọn
          </p>
        </div>
      </div>

      <div className="glass-card p-6">
        <Tabs defaultValue="my-profile">
          <TabsList>
            {finalTabs.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.title}
              </TabsTrigger>
            ))}
          </TabsList>
          {finalTabs.map((tab) => (
            <TabsContent key={tab.value} value={tab.value}>
              <tab.component />
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  )
}
