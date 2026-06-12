package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.StringReader;

class ExtendedBufferedReader_1_3Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        StringReader stringReader = new StringReader("Hello\nWorld");
        extendedBufferedReader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        int result = extendedBufferedReader.read();
        Assertions.assertEquals('H', result);
    }

    @Test
    void testRead_AfterRead() throws Exception {
        extendedBufferedReader.read(); // Read first character
        int result = extendedBufferedReader.read();
        Assertions.assertEquals('e', result);
    }

    @Test
    void testRead_AfterEndOfStream() throws Exception {
        // Read until the end of the stream
        while (extendedBufferedReader.read() != ExtendedBufferedReader.END_OF_STREAM) {}
        int result = extendedBufferedReader.read(); // Read past the end
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testReadLine_normalCase() throws Exception {
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("Hello", line);
    }

    @Test
    void testReadLine_AfterRead() throws Exception {
        extendedBufferedReader.read(); // Read first character
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("ello", line);
    }

    @Test
    void testGetLineNumber() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        int lineNumber = invokeGetLineNumber();
        Assertions.assertEquals(1, lineNumber);
    }

    private int invokeGetLineNumber() throws Exception {
        java.lang.reflect.Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(extendedBufferedReader);
    }
}