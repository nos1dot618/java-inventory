package fun.ninth.rest;

@javax.ws.rs.Path("/orders")
public class OrderResource {

    @javax.ws.rs.GET
    @javax.ws.rs.Path("/{orderId}")
    @io.swagger.v3.oas.annotations.Operation(summary = "Get order by ID")
    public String getOrder() {
        return "ok";
    }

    @javax.ws.rs.POST
    @io.swagger.v3.oas.annotations.Operation(summary = "Create order")
    public void createOrder() {
    }
}
