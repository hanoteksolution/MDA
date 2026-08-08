import type { MobileNavScreen } from "@/api/bootstrap";
import type { RootStackParamList } from "@/navigation/types";

/** Local screen registry — ids must match backend MobileNavService catalog. */
export const GYM_MEMBER_SCREEN_IDS = [
  "gym_home",
  "gym_qr",
  "gym_attendance",
  "gym_workouts",
  "gym_classes",
] as const;

export type GymMemberScreenId = (typeof GYM_MEMBER_SCREEN_IDS)[number];

const ROUTE_BY_SCREEN_ID: Record<GymMemberScreenId, keyof RootStackParamList> = {
  gym_home: "Home",
  gym_qr: "Qr",
  gym_attendance: "Attendance",
  gym_workouts: "Workouts",
  gym_classes: "Classes",
};

export function hasScreen(screens: MobileNavScreen[] | undefined, id: string): boolean {
  return (screens ?? []).some((s) => s.id === id);
}

export function navButtonsFromScreens(screens: MobileNavScreen[] | undefined) {
  const allowed = new Set((screens ?? []).map((s) => s.id));
  return (Object.keys(ROUTE_BY_SCREEN_ID) as GymMemberScreenId[])
    .filter((id) => id !== "gym_home" && allowed.has(id))
    .map((id) => {
      const remote = (screens ?? []).find((s) => s.id === id);
      return {
        id,
        label: remote?.label ?? id,
        route: ROUTE_BY_SCREEN_ID[id],
      };
    });
}
