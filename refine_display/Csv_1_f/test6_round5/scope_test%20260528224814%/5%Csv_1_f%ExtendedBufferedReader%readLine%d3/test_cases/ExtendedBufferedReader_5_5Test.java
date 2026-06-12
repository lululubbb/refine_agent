package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.io.IOException;

class ExtendedBufferedReader_5_5Test {

    @Test
    void testReadLine_normalCase() throws Exception {
        String input = "Hello, World!\nThis is a test.";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        String line2 = reader.readLine();

        Assertions.assertEquals("Hello, World!", line1);
        Assertions.assertEquals("This is a test.", line2);
    }

    @Test
    void testReadLine_emptyLine() throws Exception {
        String input = "\nThis is a test.";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        String line2 = reader.readLine();

        Assertions.assertEquals("", line1);
        Assertions.assertEquals("This is a test.", line2);
    }

    @Test
    void testReadLine_endOfStream() throws Exception {
        String input = "Hello, World!";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        String line1 = reader.readLine();
        String line2 = reader.readLine(); // This should reach end of stream

        Assertions.assertEquals("Hello, World!", line1);
        Assertions.assertNull(line2);
    }

    @Test
    void testReadLine_multipleLines() throws Exception {
        String input = "Line 1\nLine 2\nLine 3";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        Assertions.assertEquals("Line 1", reader.readLine());
        Assertions.assertEquals("Line 2", reader.readLine());
        Assertions.assertEquals("Line 3", reader.readLine());
    }

    @Test
    void testReadLine_lastCharTracking() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));

        reader.readLine(); // Read "Hello"
        int lastCharAfterFirstLine = reader.getLastChar();

        Assertions.assertEquals('o', lastCharAfterFirstLine); // last char of "Hello"

        reader.readLine(); // Read "World"
        int lastCharAfterSecondLine = reader.getLastChar();

        Assertions.assertEquals('d', lastCharAfterSecondLine); // last char of "World"
    }
}