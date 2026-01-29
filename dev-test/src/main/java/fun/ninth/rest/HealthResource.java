package fun.ninth.rest;

import javax.ws.rs.GET;
import javax.ws.rs.Path;

import io.swagger.v3.oas.annotations.Operation;

@Path("/health")
public class HealthResource {

    @GET
    @Operation(summary = "Health check endpoint")
    public String health() {
        return "ok";
    }
}
