package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_2Test {

    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        Reader reader = new StringReader("Hello\nWorld");
        extendedBufferedReader = new ExtendedBufferedReader(reader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        int result = extendedBufferedReader.read();
        Assertions.assertEquals('H', result);
    }

    @Test
    void testRead_endOfStream() throws Exception {
        extendedBufferedReader.read(); // Read first character
        extendedBufferedReader.read(); // Read second character
        extendedBufferedReader.read(); // Read third character
        extendedBufferedReader.read(); // Read fourth character
        extendedBufferedReader.read(); // Read fifth character
        extendedBufferedReader.read(); // Read newline
        extendedBufferedReader.read(); // Read first character of second line
        extendedBufferedReader.read(); // Read second character of second line
        extendedBufferedReader.read(); // Read third character of second line
        extendedBufferedReader.read(); // Read fourth character of second line
        extendedBufferedReader.read(); // Read fifth character of second line
        int result = extendedBufferedReader.read(); // Should be end of stream
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testReadAgain() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(extendedBufferedReader);
        Assertions.assertNotEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testRead_charArray_normalCase() throws Exception {
        char[] buf = new char[10];
        int length = extendedBufferedReader.read(buf, 0, 5);
        Assertions.assertEquals(5, length);
        Assertions.assertArrayEquals(new char[]{'H', 'e', 'l', 'l', 'o', '\u0000', '\u0000', '\u0000', '\u0000', '\u0000'}, buf);
    }

    @Test
    void testReadLine_normalCase() throws Exception {
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("Hello", line);
    }

    @Test
    void testLookAhead() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        int result = (int) method.invoke(extendedBufferedReader);
        Assertions.assertNotEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testGetLineNumber() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        int result = (int) method.invoke(extendedBufferedReader);
        Assertions.assertEquals(1, result);
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        String line = extendedBufferedReader.readLine(); // Read second line
        Assertions.assertNull(line); // Should be null at end of stream
    }
}