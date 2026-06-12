package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;

class ExtendedBufferedReader_3_4Test {

    @Test
    void testReadAgain_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        reader.setLastChar(ExtendedBufferedReader.UNDEFINED);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, reader.readAgain());
    }

    @Test
    void testReadAgain_afterSettingLastChar() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        reader.setLastChar(5);
        Assertions.assertEquals(5, reader.readAgain());
    }

    @Test
    void testReadAgain_afterSettingLastCharToEndOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        reader.setLastChar(ExtendedBufferedReader.END_OF_STREAM);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.readAgain());
    }
}