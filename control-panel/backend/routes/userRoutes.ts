import { Router } from 'express';
import API from '../controller/userApi.js';
import { wrapMiddleware, adminAuth } from '../utils.js';

const router = Router();

router.post("/", wrapMiddleware(adminAuth, API.createUser))
router.get("/", wrapMiddleware(adminAuth, API.fetchAllUsers))
router.put("/", wrapMiddleware(adminAuth, API.updateUser))
router.delete("/:id", wrapMiddleware(adminAuth, API.deleteUser))

export default router