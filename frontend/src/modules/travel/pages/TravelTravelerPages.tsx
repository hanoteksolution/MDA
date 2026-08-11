import { Detail, Form, List } from "./TravelCrudPages";
export const TravelTravelerListPage = () => <List kind="travelers" />;
export const TravelTravelerNewPage = () => <Form kind="travelers" />;
export const TravelTravelerEditPage = () => <Form kind="travelers" edit />;
export const TravelTravelerDetailPage = () => <Detail kind="travelers" />;
