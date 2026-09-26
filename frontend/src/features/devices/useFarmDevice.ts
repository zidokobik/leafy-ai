import { useState, useEffect } from "react";

import { cameraApi } from "@/api/camera";
import { apiConfig } from "@/api/config";
import type { CameraImage } from "@/api/contracts";

// --- Types ---
export type DeviceType = "camera" | "pump" | "doser" | "light" | "sensor";
export type DeviceStatus = "online" | "offline" | "warning";

export interface Device {
  id: string;
  name: string;
  type: DeviceType;
  status: DeviceStatus;
  isActive: boolean;
  metrics: string;
}

// --- Mock Data ---
const mockDevices: Device[] = [
  { id: "sensor_climate", name: "Greenhouse Climate", type: "sensor", status: "online", isActive: true, metrics: "Temp: 24.5°C | Hum: 62%" },
  { id: "sensor_water", name: "Water Quality", type: "sensor", status: "online", isActive: true, metrics: "pH: 6.2 | EC: 1250 / 1300 µS/cm" },
  { id: "sensor_temp", name: "Water Temp", type: "sensor", status: "online", isActive: true, metrics: "19.5°C" },
  { id: "sensor_tank", name: "Main Reservoir", type: "sensor", status: "online", isActive: true, metrics: "Level: 45 cm" },
  { id: "pump_1", name: "Irrigation Pump", type: "pump", status: "online", isActive: true, metrics: "Target EC: 1300 µS/cm" },
  { id: "doser_ph", name: "pH Doser (Up/Down)", type: "doser", status: "online", isActive: false, metrics: "Last dose: 2 hrs ago" },
  { id: "doser_nutrients", name: "Nutrient Doser (A+B)", type: "doser", status: "online", isActive: false, metrics: "Auto-dosing active" },
  { id: "light_main", name: "Main Grow Lights", type: "light", status: "online", isActive: true, metrics: "Intensity: 85% | Schedule: 18/6" },
  { id: "level1_camera1", name: "Level 1 · Camera 1", type: "camera", status: "online", isActive: true, metrics: "1080p / 30fps" },
  { id: "level1_camera2", name: "Level 1 · Camera 2", type: "camera", status: "online", isActive: true, metrics: "1080p / 30fps" },
  { id: "level1_camera3", name: "Level 1 · Camera 3", type: "camera", status: "online", isActive: true, metrics: "720p / 24fps" },
  { id: "level2_camera2", name: "Level 2 · Camera 2", type: "camera", status: "online", isActive: true, metrics: "1080p / 30fps" },
];


export type CameraImagesStatus = "loading" | "ready" | "error";

export function useFarmDevices() {
  const [devices, setDevices] = useState<Device[]>(mockDevices);
  const [cameraImages, setCameraImages] = useState<Record<string, CameraImage>>({});
  const [cameraStatus, setCameraStatus] = useState<CameraImagesStatus>("loading");

  useEffect(() => {
    const controller = new AbortController();

    async function fetchLatestImages() {
      try {
        const cameras = await cameraApi.getLatest(controller.signal);
        setCameraImages(Object.fromEntries(cameras.map((camera) => [camera.id, camera])));
        setCameraStatus("ready");
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error("Failed to fetch camera images:", error);
        setCameraStatus("error");
      }
    }

    fetchLatestImages();
    const interval = window.setInterval(fetchLatestImages, apiConfig.cameraPollMs);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, []);

  const toggleDevice = (id: string) => {
    setDevices(devices.map(dev => 
      dev.id === id ? { ...dev, isActive: !dev.isActive } : dev
    ));
  };

  return {
    devices,
    cameraImages,
    cameraStatus,
    toggleDevice
  };
}