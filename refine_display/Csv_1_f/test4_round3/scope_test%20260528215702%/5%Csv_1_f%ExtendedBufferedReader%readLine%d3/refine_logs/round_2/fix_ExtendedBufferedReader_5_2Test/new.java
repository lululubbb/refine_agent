package org.apache.commons.csv;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_5_2Test {

    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        String input = "Hello\nWorld\n";
        Reader stringReader = new StringReader(input);
        extendedBufferedReader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testReadLine_normalCase() throws Exception {
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("Hello", line);
    }

    @Test
    void testReadLine_secondLine() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        String line = extendedBufferedReader.readLine(); // Read second line
        Assertions.assertEquals("World", line);
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "Hello\n\nWorld\n";
        Reader stringReader = new StringReader(input);
        extendedBufferedReader = new ExtendedBufferedReader(stringReader);

        extendedBufferedReader.readLine(); // Read first line
        String line = extendedBufferedReader.readLine(); // Read empty line
        Assertions.assertEquals("", line);
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "Hello\nWorld\n";
        Reader stringReader = new StringReader(input);
        extendedBufferedReader = new ExtendedBufferedReader(stringReader);

        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        String line = extendedBufferedReader.readLine(); // Read end of stream
        Assertions.assertNull(line);
        
        // Check lastChar after reaching end of stream
        int lastChar = (int) getPrivateField("lastChar");
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastChar);
    }

    @Test
    void testReadLine_lastCharAssignment() throws Exception {
        String input = "Hello\nWorld\n";
        Reader stringReader = new StringReader(input);
        extendedBufferedReader = new ExtendedBufferedReader(stringReader);

        extendedBufferedReader.readLine(); // Read first line
        int lastChar = (int) getPrivateField("lastChar");

        Assertions.assertEquals('o', lastChar); // 'o' is the last char of "Hello"
    }

    @Test
    void testReadLine_lineCounterIncrement() throws Exception {
        int initialCounter = (int) getPrivateField("lineCounter");

        extendedBufferedReader.readLine(); // Read first line
        int updatedCounter = (int) getPrivateField("lineCounter");

        Assertions.assertEquals(initialCounter + 1, updatedCounter);
        
        extendedBufferedReader.readLine(); // Read second line
        updatedCounter = (int) getPrivateField("lineCounter");
        
        Assertions.assertEquals(initialCounter + 2, updatedCounter);
    }

    private Object getPrivateField(String fieldName) throws Exception {
        java.lang.reflect.Field field = ExtendedBufferedReader.class.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(extendedBufferedReader);
    }
}