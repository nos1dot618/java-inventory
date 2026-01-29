package fun.ninth.rest;

import javax.ws.rs.GET;
import javax.ws.rs.POST;
import javax.ws.rs.Path;

import io.swagger.v3.oas.annotations.Operation;

@Path("/users")
public class UserResource {

    @GET
    @Path("/{id}")
    @Operation(summary = "Get user by ID")
    public String getUser() {
        return "ok";
    }

    @POST
    @Operation(summary = "Create new user")
    public void createUser() {
    }

}
