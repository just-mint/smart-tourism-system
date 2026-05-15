import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
<<<<<<< HEAD
=======
import {
  clearAuthSession,
  hasAuthSession,
  markAuthSession,
} from "@/lib/auth-session"
>>>>>>> origin/main
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
<<<<<<< HEAD
  return localStorage.getItem("access_token") !== null
=======
  return hasAuthSession()
>>>>>>> origin/main
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
<<<<<<< HEAD
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)
=======
    await LoginService.loginAccessToken({
      formData: data,
    })
    markAuthSession()
>>>>>>> origin/main
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

<<<<<<< HEAD
  const logout = () => {
    localStorage.removeItem("access_token")
=======
  const logout = async () => {
    try {
      await LoginService.logout()
    } catch (e) {
      console.error("Logout failed", e)
    }
    clearAuthSession()
    queryClient.clear()
>>>>>>> origin/main
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
