package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_1Test {

    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        String input = "Hello\rWorld\nThis is a test.\n";
        Reader reader = new StringReader(input);
        extendedBufferedReader = new ExtendedBufferedReader(reader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        int firstChar = extendedBufferedReader.read();
        Assertions.assertEquals('H', firstChar);
    }

    @Test
    void testRead_newLine() throws Exception {
        extendedBufferedReader.read(); // Read 'H'
        extendedBufferedReader.read(); // Read 'e'
        extendedBufferedReader.read(); // Read 'l'
        extendedBufferedReader.read(); // Read 'l'
        extendedBufferedReader.read(); // Read 'o'
        extendedBufferedReader.read(); // Read '\r'

        int nextChar = extendedBufferedReader.read(); // Read 'W'
        Assertions.assertEquals('W', nextChar);
        
        // Verify line count increment
        int lineNumber = (int) getPrivateField("lineCounter");
        Assertions.assertEquals(1, lineNumber);
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        extendedBufferedReader.read(); // Read 'H'
        extendedBufferedReader.read(); // Read 'e'
        extendedBufferedReader.read(); // Read 'l'
        extendedBufferedReader.read(); // Read 'l'
        extendedBufferedReader.read(); // Read 'o'
        extendedBufferedReader.read(); // Read '\r'

        extendedBufferedReader.read(); // Read 'W'
        extendedBufferedReader.read(); // Read 'o'
        extendedBufferedReader.read(); // Read 'r'
        extendedBufferedReader.read(); // Read 'l'
        extendedBufferedReader.read(); // Read 'd'
        extendedBufferedReader.read(); // Read '\n'

        int lineNumber = (int) getPrivateField("lineCounter");
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testRead_endOfStream() throws Exception {
        while (extendedBufferedReader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read until the end of the stream
        }
        int endChar = extendedBufferedReader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, endChar);
    }

    @Test
    void testReadLine() throws Exception {
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("Hello", line);
        
        line = extendedBufferedReader.readLine();
        Assertions.assertEquals("World", line);
        
        line = extendedBufferedReader.readLine();
        Assertions.assertEquals("This is a test.", line);
        
        line = extendedBufferedReader.readLine();
        Assertions.assertNull(line);
    }

    @Test
    void testLookAhead() throws Exception {
        int lookAheadChar = (int) getPrivateField("lookAhead");
        Assertions.assertEquals('H', lookAheadChar);
        
        extendedBufferedReader.read(); // Read 'H'
        lookAheadChar = (int) getPrivateField("lookAhead");
        Assertions.assertEquals('e', lookAheadChar);
    }

    private Object getPrivateField(String fieldName) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(extendedBufferedReader);
    }
}