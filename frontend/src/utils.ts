import { AxiosError } from "axios"
import type { ApiError } from "./client"

type ErrorBody = {
  detail?: string | Array<{ msg?: string }>
}

const isErrorBody = (body: unknown): body is ErrorBody => {
  return typeof body === "object" && body !== null && "detail" in body
}

function extractErrorMessage(err: ApiError): string {
  if (err instanceof AxiosError) {
    return err.message
  }

  const errDetail = isErrorBody(err.body) ? err.body.detail : undefined
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    return errDetail[0].msg || "Something went wrong."
  }
  return typeof errDetail === "string" ? errDetail : "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: ApiError,
) {
  const errorMessage = extractErrorMessage(err)
  this(errorMessage)
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
