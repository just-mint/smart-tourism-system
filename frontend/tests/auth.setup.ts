import { expect, test as setup } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const authFile = "playwright/.auth/user.json"

setup("authenticate", async ({ page }) => {
  await page.goto("/login")

  await page.getByPlaceholder("admin@aegis.com").fill(firstSuperuser)
  await page.getByPlaceholder("••••••••").fill(firstSuperuserPassword)

  await Promise.all([
    page.waitForURL("/", { waitUntil: "networkidle" }),
    page.getByRole("button", { name: /Đăng nhập/i }).click(),
  ])

  await expect(page).toHaveURL("/")

  await page.context().addCookies([
    {
      name: "aegis_logged_in",
      value: "true",
      url: page.url(),
      sameSite: "Lax",
    },
  ])

  await page.context().storageState({ path: authFile })
})