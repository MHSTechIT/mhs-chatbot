import type { ServiceResult } from "../../models/ServiceResult";
import type { AskRequest } from "../../BOs/AskRequest/AskRequest";
import type { AskResponse } from "../../BOs/AskResponse/AskResponse";

export interface IChatService {
    ask(request: AskRequest): Promise<ServiceResult<AskResponse>>;
}
