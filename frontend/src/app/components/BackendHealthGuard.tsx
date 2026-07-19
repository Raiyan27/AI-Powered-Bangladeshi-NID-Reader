"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface BackendHealthGuardProps {
  children: React.ReactNode;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const POLL_INTERVAL_SECONDS = 5;
const HEALTH_TIMEOUT_MS = 8000;

export default function BackendHealthGuard({ children }: BackendHealthGuardProps) {
  const [isProd, setIsProd] = useState<boolean>(false);
  const [status, setStatus] = useState<"init" | "checking" | "sleeping" | "live">("init");
  const [retryCount, setRetryCount] = useState<number>(0);
  const [countdown, setCountdown] = useState<number>(POLL_INTERVAL_SECONDS);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

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
      setRetryCount((prev) => prev + 1);
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

  // 1-second ticker when server is sleeping
  useEffect(() => {
    if (!isProd || status !== "sleeping") return;

    const ticker = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
      setCountdown((prevCount) => {
        if (prevCount <= 1) {
          // Trigger next health check
          checkHealthRef.current();
          return POLL_INTERVAL_SECONDS;
        }
        return prevCount - 1;
      });
    }, 1000);

    return () => clearInterval(ticker);
  }, [isProd, status]);

  const handleManualRetry = () => {
    setStatus("checking");
    setCountdown(POLL_INTERVAL_SECONDS);
    checkHealth();
  };

  // 1. Non-prod mode OR Backend is verified Live: Render children with optional status pill in prod
  if (!isProd || status === "live") {
    return (
      <>
        {isProd && (
          <div className="w-full bg-emerald-50 border-b border-emerald-200 py-1.5 px-4 text-center">
            <div className="max-w-2xl mx-auto flex items-center justify-center gap-2 text-xs font-semibold text-emerald-800">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
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

  // Calculate dynamic progress bar percentage (0% to 100% per 5-second interval)
  const progressPercent = Math.min(100, Math.max(0, ((POLL_INTERVAL_SECONDS - countdown) / POLL_INTERVAL_SECONDS) * 100));

  // 3. Sleeping / Waking Up full-page UI screen in Prod mode
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-xl p-6 shadow-sm text-center space-y-6">
        {/* Graphic */}
        <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-amber-100 animate-ping opacity-75" />
          <div className="relative w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-amber-600 animate-spin"
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
          <h2 className="text-lg font-semibold text-gray-900">
            Waking up the server…
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            The backend is starting up after inactivity. On Render&apos;s free tier, cold-start takes approximately{" "}
            <span className="font-semibold text-gray-800">30–60 seconds</span>.
          </p>
        </div>

        {/* Countdown & Progress Bar Box */}
        <div className="bg-amber-50/60 rounded-lg p-4 border border-amber-100 space-y-3">
          <div className="flex items-center justify-between text-xs text-amber-900 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              Retrying in <span className="font-bold text-amber-800 font-mono text-sm">{countdown}s</span>
            </span>
            <span className="text-amber-700 font-mono">Attempt #{retryCount}</span>
          </div>

          {/* Smooth Dynamic Progress Bar */}
          <div className="w-full bg-amber-200/70 h-2 rounded-full overflow-hidden">
            <div
              className="bg-amber-500 h-full rounded-full transition-all duration-300 ease-linear"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Waiting Time Display */}
          <div className="flex items-center justify-between text-[11px] text-amber-700 font-mono pt-0.5">
            <span>Total Elapsed Wait:</span>
            <span className="font-bold text-amber-900">{elapsedSeconds}s</span>
          </div>
        </div>

        {/* Manual Retry Button */}
        <button
          type="button"
          onClick={handleManualRetry}
          className="w-full py-2.5 px-4 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 transition-all cursor-pointer shadow-sm"
        >
          Retry Now
        </button>
      </div>
    </div>
  );
}
