import { test as setup } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const authFile = "playwright/.auth/user.json"

setup("authenticate", async ({ page }) => {
  await page.goto("/login")
<<<<<<< HEAD
  await page.getByTestId("email-input").fill(firstSuperuser)
  await page.getByTestId("password-input").fill(firstSuperuserPassword)
  await page.getByRole("button", { name: "Log In" }).click()
  await page.waitForURL("/")
=======
  // Use placeholder as fallback to data-testid
  await page.getByPlaceholder("admin@aegis.com").fill(firstSuperuser)
  await page.getByPlaceholder("••••••••").fill(firstSuperuserPassword)
  await page.getByRole("button", { name: /Đăng nhập/i }).click()
  await page.waitForURL("/")
  await page.evaluate(() => {
    document.cookie = "aegis_logged_in=true; path=/; SameSite=Lax"
  })
>>>>>>> origin/main
  await page.context().storageState({ path: authFile })
})
