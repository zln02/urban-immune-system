"""지도 전용 CSS."""

from __future__ import annotations


def map_styles() -> str:
    return """
    <style>
        .risk-pulse-marker {
            position: relative;
            width: var(--pulse-size);
            height: var(--pulse-size);
            pointer-events: auto;
        }

        .risk-pulse-marker .pulse-ring {
            position: absolute;
            top: 50%;
            left: 50%;
            width: calc(var(--pulse-size) * 0.62);
            height: calc(var(--pulse-size) * 0.62);
            border-radius: 999px;
            border: 2px solid var(--pulse-color);
            background: var(--pulse-fill);
            transform: translate(-50%, -50%) scale(0.35);
            opacity: 0.9;
            animation: districtPulse var(--pulse-speed) ease-out infinite;
            box-shadow: 0 0 18px var(--pulse-shadow);
        }

        .risk-pulse-marker .pulse-ring.delay {
            animation-delay: calc(var(--pulse-speed) / 2);
        }

        .risk-pulse-marker .pulse-ring.intense {
            display: none;
        }

        .risk-pulse-marker .pulse-core {
            position: absolute;
            top: 50%;
            left: 50%;
            width: var(--core-size);
            height: var(--core-size);
            transform: translate(-50%, -50%);
            border-radius: 999px;
            background: var(--pulse-color);
            border: 2px solid rgba(255, 255, 255, 0.92);
            box-shadow:
                0 0 0 5px var(--pulse-fill),
                0 0 24px var(--pulse-shadow);
            animation: coreFloat 2.6s ease-in-out infinite;
        }

        .risk-pulse-marker.selected .pulse-core {
            border-width: 3px;
            box-shadow:
                0 0 0 7px var(--pulse-fill),
                0 0 28px var(--pulse-shadow);
        }

        .risk-pulse-marker.level-1 .pulse-ring {
            animation-name: districtBreathe;
        }

        .risk-pulse-marker.level-1 .pulse-core {
            animation-name: coreBreathe;
        }

        .risk-pulse-marker.level-2 .pulse-ring {
            animation-name: districtPulse;
        }

        .risk-pulse-marker.level-3 .pulse-ring {
            animation-name: districtPulseFast;
        }

        .risk-pulse-marker.level-3 .pulse-core {
            animation-duration: 1.9s;
        }

        .risk-pulse-marker.level-4 .pulse-ring {
            animation-name: districtAlarmPulse;
            border-width: 3px;
        }

        .risk-pulse-marker.level-4 .pulse-ring.intense {
            display: block;
            animation-delay: calc(var(--pulse-speed) / 4);
        }

        .risk-pulse-marker.level-4 .pulse-core {
            animation-name: coreAlert;
            animation-duration: 0.95s;
        }

        @keyframes districtPulse {
            0% {
                transform: translate(-50%, -50%) scale(0.35);
                opacity: 0.95;
            }
            65% {
                opacity: 0.18;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.55);
                opacity: 0;
            }
        }

        @keyframes districtBreathe {
            0% {
                transform: translate(-50%, -50%) scale(0.55);
                opacity: 0.38;
            }
            50% {
                transform: translate(-50%, -50%) scale(1.05);
                opacity: 0.12;
            }
            100% {
                transform: translate(-50%, -50%) scale(0.55);
                opacity: 0.38;
            }
        }

        @keyframes districtPulseFast {
            0% {
                transform: translate(-50%, -50%) scale(0.28);
                opacity: 1;
            }
            55% {
                opacity: 0.2;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.7);
                opacity: 0;
            }
        }

        @keyframes districtAlarmPulse {
            0% {
                transform: translate(-50%, -50%) scale(0.24);
                opacity: 1;
            }
            40% {
                opacity: 0.45;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.9);
                opacity: 0;
            }
        }

        @keyframes coreFloat {
            0%, 100% {
                transform: translate(-50%, -50%) scale(1);
            }
            50% {
                transform: translate(-50%, -50%) scale(1.08);
            }
        }

        @keyframes coreBreathe {
            0%, 100% {
                transform: translate(-50%, -50%) scale(0.96);
                opacity: 0.82;
            }
            50% {
                transform: translate(-50%, -50%) scale(1.04);
                opacity: 1;
            }
        }

        @keyframes coreAlert {
            0%, 100% {
                transform: translate(-50%, -50%) scale(0.92);
                box-shadow:
                    0 0 0 5px var(--pulse-fill),
                    0 0 18px var(--pulse-shadow);
            }
            50% {
                transform: translate(-50%, -50%) scale(1.16);
                box-shadow:
                    0 0 0 8px var(--pulse-fill),
                    0 0 32px var(--pulse-shadow);
            }
        }
    </style>
    """
