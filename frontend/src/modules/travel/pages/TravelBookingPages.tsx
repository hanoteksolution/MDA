import { Detail, Form, List } from "./TravelCrudPages";
export const TravelBookingListPage = () => <List kind="bookings" />;
export const TravelBookingNewPage = () => <Form kind="bookings" />;
export const TravelBookingEditPage = () => <Form kind="bookings" edit />;
export const TravelBookingDetailPage = () => <Detail kind="bookings" />;
