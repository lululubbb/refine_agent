package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_1Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        Reader reader = new StringReader("Line 1\nLine 2\nLine 3");
        extendedBufferedReader = new ExtendedBufferedReader(reader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        int firstChar = extendedBufferedReader.read();
        Assertions.assertEquals('L', firstChar);
        Assertions.assertEquals(0, invokeGetLineNumber());
    }

    @Test
    void testReadLine_normalCase() throws Exception {
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals("Line 1", line);
        Assertions.assertEquals(1, invokeGetLineNumber());
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        extendedBufferedReader.readLine(); // Read first line
        extendedBufferedReader.readLine(); // Read second line
        String line = extendedBufferedReader.readLine(); // Read third line
        Assertions.assertEquals("Line 3", line);
        Assertions.assertEquals(3, invokeGetLineNumber());
        Assertions.assertNull(extendedBufferedReader.readLine()); // Should return null
    }

    @Test
    void testReadAgain() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(extendedBufferedReader);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result); // Assuming readAgain returns -1 for EOF
    }

    @Test
    void testLookAhead() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        int result = (int) method.invoke(extendedBufferedReader);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result); // Assuming lookAhead returns -1 for EOF
    }

    private int invokeGetLineNumber() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(extendedBufferedReader);
    }
}