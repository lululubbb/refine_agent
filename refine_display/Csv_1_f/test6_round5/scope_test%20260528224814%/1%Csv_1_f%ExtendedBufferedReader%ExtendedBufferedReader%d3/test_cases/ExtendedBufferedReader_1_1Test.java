package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_1Test {

    @Test
    void testExtendedBufferedReader_read() throws Exception {
        String testInput = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);

        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
    }

    @Test
    void testExtendedBufferedReader_readAgain() throws Exception {
        String testInput = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));
        reader.read(); // Read first character to set lastChar
        reader.read(); // Read second character to set lastChar to 'e'

        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        
        // Assuming readAgain returns the last read character
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals('e', (char) result); // Expecting last character read as 'e'
    }

    @Test
    void testExtendedBufferedReader_read_charArray() throws Exception {
        String testInput = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));
        char[] buffer = new char[5];

        int charsRead = reader.read(buffer, 0, 5);
        Assertions.assertEquals(5, charsRead);
        Assertions.assertEquals("Hello", new String(buffer));
    }

    @Test
    void testExtendedBufferedReader_readLine_withEmptyInput() throws Exception {
        String testInput = "";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        String line = reader.readLine();
        Assertions.assertNull(line); // Expecting null for empty input
    }

    @Test
    void testExtendedBufferedReader_lookAhead() throws Exception {
        String testInput = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);
        
        int result = (int) lookAheadMethod.invoke(reader);
        Assertions.assertNotEquals(-1, result); // Assuming END_OF_STREAM is -1
    }

    @Test
    void testExtendedBufferedReader_getLineNumber() throws Exception {
        String testInput = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(testInput));

        // Read the first line
        reader.readLine();

        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        
        int lineNumber = (int) getLineNumberMethod.invoke(reader);
        Assertions.assertEquals(1, lineNumber); // Expecting line 1 after reading one line
    }
}