import { Request, Response, NextFunction } from "express";
import { RolePermissionHelper } from "../utilities/permission";
import { EPermission } from "../enum/permission.enum";
import { JwtToken } from "../utilities/jwt";
import { ResponseBuilder } from "../utilities/response";
import { Validator } from "../utilities/validation/book";
import { UserService } from "../services/user";
import { BookService } from "../services/book";
import { ERole } from "../enum/role.enum";


export const validateCreate = async (
    req: Request,
    res: Response,
    next: NextFunction
) => {
    try {
        const body = req.body;
        await Validator.create(body);
        next();
    } catch (e) {
        return new ResponseBuilder<Error>()
            .setData(e.message)
            .setStatus(false)
            .setResponse(res)
            .setResponseStatus(400)
            .build();
    }
};

export const validateEdit = async (
    req: Request,
    res: Response,
    next: NextFunction
) => {
    try {
        const body = req.body;
        await Validator.edit(body);
        next();
    } catch (e) {
        return new ResponseBuilder<Error>()
            .setData(e.message)
            .setStatus(false)
            .setResponse(res)
            .setResponseStatus(400)
            .build();
    }
};

export const can = (permission: EPermission) => {
    return async (
        req: Request,
        res: Response,
        next: NextFunction
    ) => {
        try {
            const id = Number(req.params.id);
            const body = req.body;
            const authorId = body?.authorId;
            const authorization = req.headers.authorization;
            const requestUser = JwtToken.getRequestUser(authorization);
            const roleUser = await UserService.getById(requestUser.id);
            let book = null;

            if (id) {
                book = await BookService.getById(id);
            }

            const permissions = await RolePermissionHelper.getPermissionsArrayForRole(roleUser.role);
            const havePermission = permissions.includes(permission);
            const isAuthorAdmin = book?.author?.role?.type === ERole.ADMIN;
            const isSameUser = book?.author?.id === roleUser.id;
            const isSameAuthor = book?.author?.id === roleUser.id;

            switch (permission) {
                case EPermission.ADD_BOOKS:
                    if ((!havePermission && authorId) || (isAuthorAdmin && !isSameAuthor)) {
                        throw new Error("Forbidden");
                    }
                    break;

                case EPermission.EDIT_BOOKS:
                    if ((!havePermission && !isSameUser) || (!havePermission && authorId) || (isAuthorAdmin && !isSameAuthor)) {
                        throw new Error("Forbidden");
                    }

                    body.book = book;
                    if (authorId) {
                        body.author = await UserService.getById(authorId);
                    }
                    break;

                case EPermission.REMOVE_BOOKS:
                    if ((!havePermission && !isSameUser) || (isAuthorAdmin && !isSameAuthor)) {
                        throw new Error("Forbidden");
                    }
                    break;

                default:
                    if (!havePermission) {
                        throw new Error("Forbidden");
                    }
                    break;
            }

            next();
        } catch (e) {
            return new ResponseBuilder<Error>()
                .setData(e.message)
                .setStatus(false)
                .setResponse(res)
                .setResponseStatus(403)
                .build();
        }
    }
}