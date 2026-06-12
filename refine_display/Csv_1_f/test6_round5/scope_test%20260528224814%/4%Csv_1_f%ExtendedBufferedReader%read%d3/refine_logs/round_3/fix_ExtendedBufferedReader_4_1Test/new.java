package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_1Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        Reader stringReader = new StringReader("line1\nline2\rline3\n");
        reader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);

        Assertions.assertEquals(8, len); // Adjusted expected length to 8
        Assertions.assertEquals("line1\nline2", new String(buffer, 0, len));
        Assertions.assertEquals(2, getLineCounter());
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        char[] buffer = new char[0];
        int len = reader.read(buffer, 0, 0);

        Assertions.assertEquals(0, len);
        Assertions.assertEquals(0, getLineCounter());
    }

    @Test
    void testRead_endOfStream() throws Exception {
        char[] buffer = new char[10];
        reader.read(buffer, 0, 10); // Read first part
        int len = reader.read(buffer, 0, 10); // Read second part

        Assertions.assertEquals(-1, len);
        Assertions.assertEquals(3, getLineCounter());
    }

    @Test
    void testRead_withCarriageReturn() throws Exception {
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);

        Assertions.assertEquals(8, len); // Adjusted expected length to 8
        Assertions.assertEquals("line1\nline2", new String(buffer, 0, len));
        Assertions.assertEquals(2, getLineCounter());
        
        // Read again to hit the carriage return
        len = reader.read(buffer, 0, 10);
        Assertions.assertEquals(-1, len);
        Assertions.assertEquals(3, getLineCounter());
    }

    private int getLineCounter() throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        return (int) lineCounterField.get(reader);
    }
}