import { useState, useEffect } from "react";

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


export function useFarmDevices() {
  const [devices, setDevices] = useState<Device[]>(mockDevices);
  const [cameraImages, setCameraImages] = useState<Record<string, string>>({});
  const [isFetchingImages, setIsFetchingImages] = useState(false);

  useEffect(() => {
    async function fetchLatestImages() {
      const token = import.meta.env.VITE_AWS_TOKEN || import.meta.env.AWS_TOKEN;
      const API_URL = "/images/student/latest"; 

      if (!token) return;

      try {
        setIsFetchingImages(true);
        const response = await fetch(API_URL, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        const imageMap: Record<string, string> = {};
        
        data.images.forEach((img: any) => {
          imageMap[img.camera_name] = img.image_url || img.url || img.presigned_url; 
        });

        setCameraImages(imageMap);
      } catch (error) {
        console.error("Failed to fetch images:", error);
      } finally {
        setIsFetchingImages(false);
      }
    }

    fetchLatestImages();
  }, []);

  const toggleDevice = (id: string) => {
    setDevices(devices.map(dev => 
      dev.id === id ? { ...dev, isActive: !dev.isActive } : dev
    ));
  };

  return {
    devices,
    cameraImages,
    isFetchingImages,
    toggleDevice
  };
}