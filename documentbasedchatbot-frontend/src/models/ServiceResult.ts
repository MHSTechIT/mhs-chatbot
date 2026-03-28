export const ServiceStatusCode = {
    OK: 200,
    Created: 201,
    BadRequest: 400,
    Unauthorized: 401,
    Forbidden: 403,
    NotFound: 404,
    InternalServerError: 500,
    ServiceException: 999,
    NetworkFailure: 998,
} as const;

export type ServiceStatusCodeType = typeof ServiceStatusCode[keyof typeof ServiceStatusCode];

export interface ServiceResult<T> {
    statusCode: ServiceStatusCodeType;
    message?: string;
    content?: T | null;
}
