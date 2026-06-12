package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_9_5Test {

    @Test
    public void testGetComment_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(null, record.getComment());
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("", record.getComment());
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment());
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}