"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface BackendHealthGuardProps {
  children: React.ReactNode;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CYCLE_MS = 5000;
const TICK_MS = 100;
const HEALTH_TIMEOUT_MS = 4500;

export default function BackendHealthGuard({ children }: BackendHealthGuardProps) {
  const [isProd, setIsProd] = useState<boolean>(false);
  const [status, setStatus] = useState<"init" | "checking" | "sleeping" | "live">("init");
  const [retryCount, setRetryCount] = useState<number>(1);
  const [cycleMs, setCycleMs] = useState<number>(0);
  const [totalMs, setTotalMs] = useState<number>(0);

  const isCheckingRef = useRef<boolean>(false);
  const checkHealthRef = useRef<() => Promise<void>>(async () => {});

  // Detect production mode safely on client mount
  useEffect(() => {
    const appEnv = (process.env.NEXT_PUBLIC_APP_ENV || process.env.NODE_ENV || "").toLowerCase().trim();
    const prodDetected = appEnv === "prod" || appEnv === "production";
    setIsProd(prodDetected);

    if (!prodDetected) {
      setStatus("live");
    } else {
      setStatus("checking");
    }
  }, []);

  const checkHealth = useCallback(async () => {
    if (isCheckingRef.current) return;
    isCheckingRef.current = true;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

    try {
      const response = await fetch(`${API_URL}/health`, {
        method: "GET",
        signal: controller.signal,
        cache: "no-store",
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json().catch(() => null);
        if (data && data.status === "ok") {
          setStatus("live");
          isCheckingRef.current = false;
          return;
        }
      }

      // If non-200 or status !== "ok"
      setStatus("sleeping");
    } catch {
      // Network error, timeout, or abort
      setStatus("sleeping");
    } finally {
      clearTimeout(timeoutId);
      isCheckingRef.current = false;
    }
  }, []);

  // Keep ref updated to avoid stale closures in setInterval
  useEffect(() => {
    checkHealthRef.current = checkHealth;
  }, [checkHealth]);

  // Initial check on production mount
  useEffect(() => {
    if (!isProd) return;
    checkHealth();
  }, [isProd, checkHealth]);

  // 100ms fluid animation ticker when server is sleeping
  useEffect(() => {
    if (!isProd || status !== "sleeping") return;

    const ticker = setInterval(() => {
      setTotalMs((prev) => prev + TICK_MS);
      setCycleMs((prevCycle) => {
        const nextCycle = prevCycle + TICK_MS;
        if (nextCycle >= CYCLE_MS) {
          // Increment attempt count immediately when the 5s counter restarts
          setRetryCount((prev) => prev + 1);
          // Trigger health check at the start of each new 5s cycle
          checkHealthRef.current();
          return 0;
        }
        return nextCycle;
      });
    }, TICK_MS);

    return () => clearInterval(ticker);
  }, [isProd, status]);

  const handleManualRetry = () => {
    setRetryCount((prev) => prev + 1);
    setStatus("checking");
    setCycleMs(0);
    checkHealth();
  };

  // 1. Non-prod mode OR Backend is verified Live: Render children with optional status pill in prod
  if (!isProd || status === "live") {
    return (
      <>
        {isProd && (
          <div className="w-full bg-emerald-50/80 border-b border-emerald-200/80 py-2 px-4 text-center backdrop-blur-sm">
            <div className="max-w-2xl mx-auto flex items-center justify-center gap-2 text-xs font-semibold text-emerald-800">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </span>
              <span>Backend Status: Online &amp; Live</span>
            </div>
          </div>
        )}
        {children}
      </>
    );
  }

  // 2. Initial checking state in Prod mode
  if (status === "checking" || status === "init") {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 py-12 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto" />
        <div className="space-y-1">
          <p className="text-sm font-semibold text-gray-800">Checking backend status…</p>
          <p className="text-xs text-gray-400">Verifying API availability on Render</p>
        </div>
      </div>
    );
  }

  // Calculate fluid progress bar percentage (0% -> 100%) and remaining seconds
  const progressPercent = Math.min(100, Math.max(0, (cycleMs / CYCLE_MS) * 100));
  const secondsRemaining = Math.max(1, Math.ceil((CYCLE_MS - cycleMs) / 1000));
  const totalElapsedSec = Math.floor(totalMs / 1000);

  // 3. Sleeping / Waking Up full-page UI screen in Prod mode (Indigo/Blue Theme)
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white border border-gray-200/90 rounded-2xl p-7 shadow-xl shadow-blue-500/5 text-center space-y-6">
        {/* Graphic */}
        <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-blue-100 animate-ping opacity-60" />
          <div className="relative w-12 h-12 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center shadow-inner">
            <svg
              className="w-6 h-6 text-blue-600 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          </div>
        </div>

        {/* Informative Text */}
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-gray-900 tracking-tight">
            Waking up the server…
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed max-w-xs mx-auto">
            The backend is spinning up after inactivity. On Render&apos;s free tier, cold-start takes approximately{" "}
            <span className="font-semibold text-gray-800">30–60 seconds</span>.
          </p>
        </div>

        {/* Fluid Progress Box */}
        <div className="bg-slate-50/90 rounded-xl p-4 border border-gray-200/80 space-y-3 shadow-inner">
          <div className="flex items-center justify-between text-xs text-gray-700 font-medium">
            <span className="flex items-center gap-1.5 font-semibold text-blue-700">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              Retrying in <span className="font-bold text-blue-900 font-mono">{secondsRemaining}s</span>
            </span>
            <span className="text-gray-500 font-mono">Attempt #{retryCount}</span>
          </div>

          {/* Smooth Fluid Progress Bar (0% to 100% left-to-right) */}
          <div className="w-full bg-gray-200/80 h-2.5 rounded-full overflow-hidden p-0.5 border border-gray-200/50">
            <div
              className="bg-gradient-to-r from-blue-500 to-indigo-600 h-full rounded-full transition-all duration-100 ease-linear shadow-sm"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Waiting Time Display */}
          <div className="flex items-center justify-between text-[11px] text-gray-500 font-mono pt-0.5">
            <span>Total Elapsed Wait:</span>
            <span className="font-bold text-gray-800">{totalElapsedSec}s</span>
          </div>
        </div>

        {/* Manual Retry Button */}
        <button
          type="button"
          onClick={handleManualRetry}
          className="w-full py-3 px-4 rounded-xl text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 active:from-blue-800 active:to-indigo-800 transition-all duration-150 cursor-pointer shadow-md shadow-blue-500/20"
        >
          Retry Now
        </button>
      </div>
    </div>
  );
}
