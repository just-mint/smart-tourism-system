import { expect, type Page, type Route, test } from "@playwright/test"

const json = async (route: Route, body: unknown, status = 200) => {
  await route.fulfill({ status, json: body })
}

const jsonAfter = async (
  route: Route,
  body: unknown,
  delayMs = 300,
  status = 200,
) => {
  await new Promise((resolve) => setTimeout(resolve, delayMs))
  await json(route, body, status)
}

const mockAuthenticatedUser = async (page: Page) => {
  await page.addInitScript(() => {
    document.cookie = "aegis_logged_in=true; path=/; SameSite=Lax"
  })

  await page.route("**/api/v1/users/me", (route) =>
    json(route, {
      id: 1,
      email: "admin@aegis.com",
      is_active: true,
      is_superuser: true,
      full_name: "Admin",
    }),
  )
}

const mockInventoryLocks = async (page: Page) => {
  await page.route("**/api/v1/inventory/locks*", (route) => json(route, []))
}

const mockInventoryCatalog = async (
  page: Page,
  {
    stores = [{ store_id: 1, name: "Mock Store", address: "123 Street" }],
    products = [
      {
        product_id: 101,
        store_id: 1,
        name: "Mock Product",
        price: 100000,
        stock: 10,
      },
    ],
  } = {},
) => {
  await mockInventoryLocks(page)
  await page.route("**/api/v1/inventory/stores*", (route) =>
    json(route, stores),
  )
  await page.route("**/api/v1/inventory/stores/1/products*", (route) =>
    json(route, products),
  )
}

test.describe("O2O domain routes", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("smoke renders every new O2O route", async ({ page }) => {
    await mockInventoryCatalog(page)
    await page.route("**/api/v1/vision/closet*", (route) => json(route, []))

    await page.goto("/culture")
    await expect(page.getByTestId("culture-search-input")).toBeVisible()

    await page.goto("/spatial")
    await expect(page.getByTestId("spatial-scan-button")).toBeVisible()

    await page.goto("/inventory")
    await expect(page.getByText("Mock Store")).toBeVisible()
    await expect(page.getByText("Mock Product")).toBeVisible()

    await page.goto("/vision")
    await expect(page.getByTestId("vision-upload-zone")).toBeVisible()

    await page.goto("/itinerary")
    await expect(page.getByTestId("itinerary-generate-button")).toBeVisible()
  })
})

test.describe("Culture domain API states", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("search shows loading, empty, error, and success states", async ({
    page,
  }) => {
    let mode: "loading" | "empty" | "error" | "success" = "loading"

    await page.route("**/api/v1/culture/places/search*", async (route) => {
      if (mode === "loading") {
        await jsonAfter(route, [], 300)
        return
      }
      if (mode === "error") {
        await json(route, { detail: "boom" }, 500)
        return
      }
      await json(
        route,
        mode === "success"
          ? [
              {
                id: 1,
                name: "Hoan Kiem Lake",
                category: "Tourism",
                lat: 21.0285,
                lon: 105.8542,
              },
            ]
          : [],
      )
    })

    await page.goto("/culture")
    await page.getByTestId("culture-search-input").fill("lake")
    await page.locator('form button[type="submit"]').click()
    await expect(page.locator('form button[type="submit"]')).toBeDisabled()
    await expect(page.getByText("Hoan Kiem Lake")).not.toBeVisible()

    mode = "empty"
    await page.getByTestId("culture-search-input").fill("missing")
    await page.locator('form button[type="submit"]').click()
    await expect(page.getByText("Hoan Kiem Lake")).not.toBeVisible()

    mode = "error"
    await page.getByTestId("culture-search-input").fill("error")
    await page.locator('form button[type="submit"]').click()
    await expect(page.getByTestId("culture-search-input")).toBeEditable()

    mode = "success"
    await page.getByTestId("culture-search-input").fill("lake")
    await page.locator('form button[type="submit"]').click()
    await expect(page.getByText("Hoan Kiem Lake")).toBeVisible()
  })
})

test.describe("Spatial domain API states", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("nearby scan handles loading, empty, error, and success responses", async ({
    page,
  }) => {
    let mode: "loading" | "empty" | "error" | "success" = "loading"

    await page.route("**/api/v1/spatial/nearby-places*", async (route) => {
      if (mode === "loading") {
        await jsonAfter(route, {
          user_location: { lat: 21.0285, lon: 105.8542 },
          search_radius_meters: 2000,
          total_found: 0,
          places: [],
        })
        return
      }
      if (mode === "error") {
        await json(route, { detail: "boom" }, 500)
        return
      }
      await json(route, {
        user_location: { lat: 21.0285, lon: 105.8542 },
        search_radius_meters: 2000,
        total_found: mode === "success" ? 1 : 0,
        places:
          mode === "success"
            ? [
                {
                  id: 1,
                  name: "Mock Place",
                  category: "Museum",
                  lat: 21.029,
                  lon: 105.855,
                  distance_meters: 120,
                },
              ]
            : [],
      })
    })

    await page.goto("/spatial")
    await page.getByTestId("spatial-scan-button").click()
    await expect(page.getByTestId("spatial-scan-button")).toBeDisabled()

    mode = "empty"
    await page.getByTestId("spatial-scan-button").click()
    await expect(page.getByText("Mock Place")).not.toBeVisible()

    mode = "error"
    await page.getByTestId("spatial-scan-button").click()
    await expect(page.getByTestId("spatial-scan-button")).toBeEnabled()

    mode = "success"
    await page.getByTestId("spatial-scan-button").click()
    await expect(page.getByText("Mock Place")).toBeVisible()
  })
})

test.describe("Inventory domain API states", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("catalog handles loading, empty, error, and success responses", async ({
    page,
  }) => {
    await mockInventoryLocks(page)
    let mode: "loading" | "empty" | "error" | "success" = "loading"

    await page.route("**/api/v1/inventory/stores", async (route) => {
      if (mode === "loading") {
        await jsonAfter(route, [{ store_id: 1, name: "Slow Store" }], 1500)
        return
      }
      if (mode === "error") {
        await json(route, { detail: "boom" }, 500)
        return
      }
      await json(
        route,
        mode === "empty" ? [] : [{ store_id: 1, name: "Store A" }],
      )
    })
    await page.route("**/api/v1/inventory/stores/1/products*", (route) =>
      json(route, [
        {
          product_id: 1,
          store_id: 1,
          name: "Item X",
          price: 50000,
          stock: 5,
        },
      ]),
    )

    await page.goto("/inventory")
    await expect(page.locator(".animate-pulse").first()).toBeVisible()

    mode = "empty"
    await page.reload()
    await expect(page.getByText(/Kh.*ng t.*m|No products found/i)).toBeVisible()

    mode = "error"
    await page.reload()
    await expect(page.getByText(/Kh.*ng t.*m|No products found/i)).toBeVisible()

    mode = "success"
    await page.reload()
    await expect(page.getByText("Store A")).toBeVisible()
    await expect(page.getByText("Item X")).toBeVisible()
  })

  test("checkout copy never says paid before a pending order is paid", async ({
    page,
  }) => {
    await mockInventoryCatalog(page, {
      stores: [{ store_id: 1, name: "Store A", address: "123 Street" }],
      products: [
        { product_id: 1, store_id: 1, name: "Item X", price: 50000, stock: 5 },
      ],
    })
    await page.route("**/api/v1/inventory/lock*", (route) =>
      json(route, {
        message: "Locked",
        lock_id: 1,
        expires_at: new Date(Date.now() + 900000).toISOString(),
      }),
    )
    await page.route("**/api/v1/inventory/orders*", (route) =>
      json(route, {
        order_id: 123,
        order_code: "ORD-TEST",
        status: "pending",
        total_amount: 50000,
        vietqr_url: "https://api.vietqr.io/mock.png",
      }),
    )

    await page.goto("/inventory")
    await page.getByTestId("reserve-button").first().click()
    const dialog = page.getByRole("dialog")
    await dialog.locator("input").nth(0).fill("Test User")
    await dialog.locator("input").nth(1).fill("0900000000")
    await dialog.locator("textarea").fill("Hanoi, Vietnam")
    await dialog.getByRole("button", { name: /VietQR/i }).click()

    await expect(dialog.getByText(/ORD-TEST/i)).toBeVisible()
    await expect(dialog.getByAltText("VietQR")).toBeVisible()
    await expect(dialog.getByText(/scan|qu/i).first()).toBeVisible()

    const content = (await page.content()).toLowerCase()
    expect(content).not.toContain("successfully paid")
    expect(content).not.toContain("đã thanh toán")
    expect(content).not.toContain("da thanh toan")
  })
})

test.describe("Vision domain API states", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("closet handles loading, empty, error, and success responses", async ({
    page,
  }) => {
    let mode: "loading" | "empty" | "error" | "success" = "loading"

    await page.route("**/api/v1/vision/closet*", async (route) => {
      if (mode === "loading") {
        await jsonAfter(route, [], 1500)
        return
      }
      if (mode === "error") {
        await json(route, { detail: "boom" }, 500)
        return
      }
      await json(
        route,
        mode === "success"
          ? [
              {
                id: 7,
                image_path: "mock-closet.png",
                created_at: "2026-05-16T00:00:00Z",
              },
            ]
          : [],
      )
    })

    await page.goto("/vision")
    const scanTab = page.getByRole("button", { name: /Qu|AI/ }).first()
    const closetTab = page.getByRole("button", { name: /Tá|ảo|Closet/ }).first()

    await closetTab.click()
    await expect(page.locator(".animate-spin").first()).toBeVisible()

    mode = "empty"
    await scanTab.click()
    await closetTab.click()
    await expect(page.getByText("ID: 7")).not.toBeVisible()

    mode = "error"
    await scanTab.click()
    await closetTab.click()
    await expect(closetTab).toBeVisible()

    mode = "success"
    await scanTab.click()
    await closetTab.click()
    await expect(page.getByText("ID: 7")).toBeVisible()
  })
})

test.describe("Itinerary domain API states", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page)
  })

  test("planner handles loading, empty, error, and success responses", async ({
    page,
  }) => {
    let mode: "loading" | "empty" | "error" | "success" = "loading"

    await page.route("**/api/v1/planner/generate", async (route) => {
      if (mode === "loading") {
        await jsonAfter(route, {
          status: "ok",
          optimized_route: [],
          metrics: {
            total_price: 0,
            total_distance_km: 0,
            routing_fallback_used: false,
          },
          total_candidates: 0,
        })
        return
      }
      if (mode === "error") {
        await json(route, { detail: "boom" }, 500)
        return
      }
      await json(route, {
        status: "ok",
        optimized_route:
          mode === "success"
            ? [
                {
                  order: 1,
                  store_id: 1,
                  name: "Planner Stop",
                  category: "Market",
                  address: "1 Route Way",
                  lat: 21.03,
                  lon: 105.85,
                  products: [
                    { product_id: 1, name: "Route Item", price: 25000 },
                  ],
                },
              ]
            : [],
        metrics: {
          total_price: mode === "success" ? 25000 : 0,
          total_distance_km: mode === "success" ? 1.2 : 0,
          routing_fallback_used: false,
        },
        total_candidates: mode === "success" ? 1 : 0,
      })
    })

    await page.goto("/itinerary")
    await page.getByTestId("itinerary-generate-button").click()
    await expect(page.getByTestId("itinerary-generate-button")).toBeDisabled()

    mode = "empty"
    await page.getByTestId("itinerary-generate-button").click()
    await expect(page.getByText("Planner Stop")).not.toBeVisible()

    mode = "error"
    await page.getByTestId("itinerary-generate-button").click()
    await expect(page.getByTestId("itinerary-generate-button")).toBeEnabled()

    mode = "success"
    await page.getByTestId("itinerary-generate-button").click()
    await expect(page.getByText("Planner Stop")).toBeVisible()
    await page.getByText("Planner Stop").click()
    await expect(page.getByText("Route Item")).toBeVisible()
  })
})
