import { Detail, Form, List } from "./TravelCrudPages";
export const TravelPackageListPage = () => <List kind="packages" />;
export const TravelPackageNewPage = () => <Form kind="packages" />;
export const TravelPackageEditPage = () => <Form kind="packages" edit />;
export const TravelPackageDetailPage = () => <Detail kind="packages" />;
