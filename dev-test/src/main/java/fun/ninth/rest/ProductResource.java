package fun.ninth.rest;

import javax.ws.rs.GET;
import javax.ws.rs.Path;

@Path("/products")
public class ProductResource {

    @GET
    @javax.ws.rs.Path("/{sku}")
    @io.swagger.v3.oas.annotations.Operation(summary = "Get product by SKU")
    public String getProduct() {
        return "ok";
    }
}
