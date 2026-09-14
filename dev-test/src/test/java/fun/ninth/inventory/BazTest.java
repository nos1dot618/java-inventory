package fun.ninth;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class BazTest {

    @Test
    void testProcess() {
        Baz baz = new Baz();
        String result = baz.process("hello");
        assertEquals("", result); // placeholder
    }

    // NOTE: Missing test for Baz.compute
    // @Test
    // void testCompute() {
    //     Baz baz = new Baz();
    //     double value = baz.compute(2.0, 3.0);
    //     assertEquals(0.0, value); // placeholder
    // }

    @Test
    void testCreateThrowsException() {
        // TODO: implement
    }

}
