import { expect, test } from "@playwright/test"

test.describe("O2O Domains Smoke Tests", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication state
    await page.addInitScript(() => {
      document.cookie = "aegis_logged_in=true; path=/; SameSite=Lax"
    })

    await page.route("**/api/v1/users/me", async (route) => {
      await route.fulfill({
        json: {
          id: 1,
          email: "admin@aegis.com",
          is_active: true,
          is_superuser: true,
          full_name: "Admin",
        },
      })
    })
  })

  test("Culture & Tourism page smoke test", async ({ page }) => {
    await page.route("**/api/v1/culture/places/search*", async (route) => {
      await route.fulfill({
        json: [
          {
            id: 1,
            name: "Hoan Kiem Lake",
            category: "Tourism",
            lat: 21.0285,
            lon: 105.8542,
          },
        ],
      })
    })

    await page.goto("/culture")
    await expect(page.getByText(/Văn hóa & Di sản/i)).toBeVisible({
      timeout: 15000,
    })

    // Test search interaction
    await page
      .locator('input[data-testid="culture-search-input"]')
      .fill("Hoan Kiem")
    await expect(page.getByText("Hoan Kiem Lake")).toBeVisible({
      timeout: 10000,
    })
  })

  test("Spatial Operations page smoke test", async ({ page }) => {
    await page.route("**/api/v1/spatial/nearby-places*", async (route) => {
      await route.fulfill({
        json: {
          user_location: { lat: 21.0285, lon: 105.8542 },
          search_radius_meters: 2000,
          total_found: 1,
          places: [{ id: 1, name: "Mock Place", lat: 21.029, lon: 105.855 }],
        },
      })
    })

    await page.goto("/spatial")
    await expect(page.getByText(/SPATIAL_OPS/i)).toBeVisible({ timeout: 15000 })

    // Trigger scan
    await page.getByTestId("spatial-scan-button").click()
    await expect(page.getByText(/Tìm thấy 1 địa điểm/i)).toBeVisible({
      timeout: 10000,
    })
  })

  test("Inventory & Market page smoke test", async ({ page }) => {
    await page.route("**/api/v1/inventory/stores*", async (route) => {
      await route.fulfill({
        json: [
          {
            store_id: 1,
            name: "Mock Store",
            address: "123 Street",
            lat: 21,
            lon: 105,
          },
        ],
      })
    })
    await page.route(
      "**/api/v1/inventory/stores/1/products*",
      async (route) => {
        await route.fulfill({
          json: [
            { product_id: 101, name: "Mock Product", price: 100000, stock: 10 },
          ],
        })
      },
    )

    await page.goto("/inventory")
    await expect(page.getByText(/O2O Market/i)).toBeVisible({ timeout: 15000 })
    await expect(page.getByText(/Mock Store/i)).toBeVisible()
    await expect(page.getByText(/Mock Product/i)).toBeVisible()
  })

  test("AI Vision Scan page smoke test", async ({ page }) => {
    await page.goto("/vision")
    await expect(page.getByText(/Vision & Closet/i)).toBeVisible({
      timeout: 15000,
    })
  })

  test("Itinerary Planner page smoke test", async ({ page }) => {
    await page.goto("/itinerary")
    await expect(page.getByText(/SMART_PLANNER/i)).toBeVisible({
      timeout: 15000,
    })
  })

  test("Checkout flow doesn't say 'paid' before payment", async ({ page }) => {
    await page.route("**/api/v1/inventory/stores*", async (route) => {
      await route.fulfill({ json: [{ store_id: 1, name: "Store A" }] })
    })
    await page.route(
      "**/api/v1/inventory/stores/1/products*",
      async (route) => {
        await route.fulfill({
          json: [{ product_id: 1, name: "Item X", price: 50000, stock: 5 }],
        })
      },
    )
    await page.route("**/api/v1/inventory/lock*", async (route) => {
      await route.fulfill({
        json: {
          message: "Locked",
          lock_id: 1,
          expires_at: new Date(Date.now() + 900000).toISOString(),
        },
      })
    })
    await page.route("**/api/v1/inventory/orders*", async (route) => {
      await route.fulfill({
        json: {
          order_id: 123,
          order_code: "ORD-TEST",
          status: "pending",
          total_amount: 50000,
          vietqr_url: "https://api.vietqr.io/mock.png",
        },
      })
    })

    await page.goto("/inventory")
    await page.getByTestId("reserve-button").first().click()

    await page.getByPlaceholder("John Doe").fill("Test User")
    await page.getByPlaceholder("0912345678").fill("0900000000")
    await page.getByPlaceholder("123 Main St...").fill("Hanoi, Vietnam")

    await page.getByRole("button", { name: /Place Order via VietQR/i }).click()

    await expect(page.getByText(/Order Created/i)).toBeVisible({
      timeout: 10000,
    })
    await expect(
      page.getByText(/Scan with any banking app to complete payment/i),
    ).toBeVisible()

    const content = await page.content()
    expect(content.toLowerCase()).not.toContain("đã thanh toán")
    expect(content.toLowerCase()).not.toContain("successfully paid")
  })
})
