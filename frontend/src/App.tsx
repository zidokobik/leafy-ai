import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AppShell } from "./components/AppShell";
import { AgentsPage } from "./features/agents/AgentsPage";
import { LoginPage } from "./features/auth/LoginPage";
import { useAuth } from "./features/auth/useAuth";
import { DevicesPage } from "./features/devices/DevicesPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { SchedulesPage } from "./features/schedules/SchedulesPage";
import { LogsPage } from "./features/logpage/LogsPage";

export default function App() {
  const auth = useAuth();

  if (auth.status === "loading") {
    return (
      <main className="grid min-h-svh place-items-center bg-background p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Opening your greenhouse...</CardTitle>
            <CardDescription role="status">
              Checking your session and loading your account.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  if (auth.status === "signedOut") return <LoginPage onSignIn={auth.signIn} />;

  if (auth.status === "error" || !auth.user) {
    return (
      <main className="grid min-h-svh place-items-center bg-background p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Account unavailable</CardTitle>
            <CardDescription>
              Unable to finish loading your Leafy account.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <Alert variant="destructive">
              <AlertTitle>Session error</AlertTitle>
              <AlertDescription>
                {auth.error || "Unable to load your account. Please try again."}
              </AlertDescription>
            </Alert>
            <Button onClick={auth.retry}>Try again</Button>
            {auth.logoutError && (
              <Alert variant="destructive">
                <AlertDescription>{auth.logoutError}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <AppShell
              key={auth.user.id}
              user={auth.user}
              signingOut={auth.signingOut}
              logoutError={auth.logoutError}
              onProfile={auth.updateProfile}
              onDeleted={() => void auth.finishAccountDeletion()}
              onLogout={() => void auth.signOut()}
            />
          }
        >
          <Route index element={<OverviewPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="schedules" element={<SchedulesPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
