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
        Assertions.assertEquals(comment, record.getComment(), "Comment should match the expected value.");
    }

    @Test
    public void testGetComment_nullComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = null;
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(null, record.getComment(), "Comment should be null.");
    }

    @Test
    public void testGetComment_emptyComment() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "";
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals("", record.getComment(), "Comment should be an empty string.");
    }

    @Test
    public void testGetComment_specialCharacters() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "!@#$%^&*()_+";
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, comment, recordNumber);
        Assertions.assertEquals(comment, record.getComment(), "Comment should match the expected special characters.");
    }

    @Test
    public void testGetComment_boundaryValues() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        
        String longComment = "Boundary comment with length 255 characters: " + "A".repeat(255);
        long recordNumber = 1;

        CSVRecord record = createCSVRecord(values, mapping, longComment, recordNumber);
        Assertions.assertEquals(longComment, record.getComment(), "Comment should match the long boundary value.");

        String emptyComment = ""; 
        record = createCSVRecord(values, mapping, emptyComment, recordNumber);
        Assertions.assertEquals(emptyComment, record.getComment(), "Comment should be an empty string.");

        String nullComment = null; 
        record = createCSVRecord(values, mapping, nullComment, recordNumber);
        Assertions.assertEquals(null, record.getComment(), "Comment should be null.");
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}