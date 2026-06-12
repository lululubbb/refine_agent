package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;

public class CSVRecord_9_4Test {

    @Test
    public void testGetComment_nonNullComment() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(null, csvRecord.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        HashMap<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, csvRecord.getComment());
    }

    private CSVRecord createCSVRecord(String[] values, HashMap<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}