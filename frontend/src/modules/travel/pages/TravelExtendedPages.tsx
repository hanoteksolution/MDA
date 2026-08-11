import { Detail, Form, List, type Kind } from "./TravelCrudPages";

const pages = (kind: Kind) => ({
  List: () => <List kind={kind} />,
  New: () => <Form kind={kind} />,
  Edit: () => <Form kind={kind} edit />,
  Detail: () => <Detail kind={kind} />,
});

export const TravelInsurancePages = pages("insurance");
export const TravelVehiclePages = pages("vehicles");
export const TravelDriverPages = pages("drivers");
export const TravelTransferPages = pages("transfers");
export const TravelItineraryPages = pages("itineraries");
export const TravelActivityPages = pages("activities");
export const TravelQuotationPages = pages("quotations");
export const TravelDocumentPages = pages("documents");
export const TravelPaymentPages = pages("payments");
export const TravelRefundPages = pages("refunds");
export const TravelExpensePages = pages("expenses");
