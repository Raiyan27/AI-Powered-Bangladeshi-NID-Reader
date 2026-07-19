"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface BackendHealthGuardProps {
  children: React.ReactNode;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const IS_PROD = process.env.NEXT_PUBLIC_APP_ENV === "prod";

const POLL_INTERVAL_MS = 5000;
const HEALTH_TIMEOUT_MS = 8000;

export default function BackendHealthGuard({ children }: BackendHealthGuardProps) {
  // In development mode (or when IS_PROD is false), initialize immediately without blocking
  const [isReady, setIsReady] = useState(!IS_PROD);
  const [isChecking, setIsChecking] = useState(IS_PROD);
  const [retryCount, setRetryCount] = useState(0);

  const isCheckingRef = useRef(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const checkHealth = useCallback(async () => {
    // Avoid creating multiple concurrent polling requests
    if (isCheckingRef.current) return;
    isCheckingRef.current = true;
    setIsChecking(true);

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
          setIsReady(true);
          setIsChecking(false);
          isCheckingRef.current = false;
          if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
          }
          return;
        }
      }

      // If response is not ok or status !== "ok"
      setIsReady(false);
    } catch {
      // Network error, timeout, or abort
      setIsReady(false);
    } finally {
      clearTimeout(timeoutId);
      setIsChecking(false);
      isCheckingRef.current = false;
      setRetryCount((prev) => prev + 1);
    }
  }, []);

  useEffect(() => {
    // Skip health check completely in non-production mode
    if (!IS_PROD) {
      setIsReady(true);
      return;
    }

    // Run initial health check immediately
    checkHealth();

    // Setup polling every 5 seconds until ready
    timerRef.current = setInterval(() => {
      checkHealth();
    }, POLL_INTERVAL_MS);

    // Clean up timer and pending state on unmount
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [checkHealth]);

  const handleManualRetry = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    checkHealth();
    timerRef.current = setInterval(() => {
      checkHealth();
    }, POLL_INTERVAL_MS);
  };

  // If backend is verified or non-prod mode, render normal application content
  if (isReady) {
    return <>{children}</>;
  }

  // Production Waking Up UI screen
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white border border-gray-200 rounded-xl p-6 shadow-sm text-center space-y-6">
        {/* Animated Server Spin-up Graphic */}
        <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-blue-100 animate-ping opacity-75" />
          <div className="relative w-12 h-12 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center">
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
          <h2 className="text-lg font-semibold text-gray-900">
            Waking up the server…
          </h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            The backend server is spinning up after a period of inactivity. This usually takes around{" "}
            <span className="font-medium text-gray-700">30–60 seconds</span> on Render&apos;s free tier.
          </p>
        </div>

        {/* Polling Indicator / Progress Bar */}
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-100 space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              {isChecking ? "Checking server health…" : "Auto-retrying every 5s"}
            </span>
            <span>Check #{retryCount}</span>
          </div>

          <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
            <div className="bg-blue-600 h-full rounded-full animate-pulse w-full" />
          </div>
        </div>

        {/* Manual Retry Button */}
        <button
          type="button"
          onClick={handleManualRetry}
          disabled={isChecking}
          className={`w-full py-2.5 px-4 rounded-lg text-xs font-semibold transition-all duration-150 ${
            isChecking
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 cursor-pointer shadow-sm"
          }`}
        >
          {isChecking ? "Checking Status…" : "Retry Now"}
        </button>
      </div>
    </div>
  );
}
